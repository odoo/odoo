import stdnum

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    _rec_names_search = ['name', 'check_number']

    # Third party check operation links
    l10n_latam_check_id = fields.Many2one(
        comodel_name='account.payment',
        string='Check',
        readonly=True, states={'draft': [('readonly', False)]},
        copy=False,
        check_company=True,
    )
    l10n_latam_check_operation_ids = fields.One2many(
        comodel_name='account.payment',
        inverse_name='l10n_latam_check_id',
        string='Check Operations',
        readonly=True,
    )
    l10n_latam_check_current_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Check Current Journal",
        compute='_compute_l10n_latam_check_current_journal', store=True,
    )
    # Warning message in case of unlogical third party check operations
    l10n_latam_check_warning_msg = fields.Text(
        compute='_compute_l10n_latam_check_warning_msg',
    )
    l10n_latam_check_number = fields.Char(
        compute='_compute_l10n_latam_check_number', inverse='_inverse_l10n_latam_check_number',
    )
    # New third party check info
    l10n_latam_check_bank_id = fields.Many2one(
        comodel_name='res.bank',
        string='Check Bank',
        compute='_compute_l10n_latam_check_bank_id', store=True, readonly=False,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
    )
    l10n_latam_check_issuer_vat = fields.Char(
        string='Check Issuer VAT',
        compute='_compute_l10n_latam_check_issuer_vat', store=True, readonly=False,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
    )
    l10n_latam_check_payment_date = fields.Date(
        string='Check Cash-In Date',
        help="Date from when you can cash in the check, turn the check into cash",
        readonly=True, states={'draft': [('readonly', False)]},
    )

    # This is a technical field for the view only
    l10n_latam_manual_checks = fields.Boolean(
        related='journal_id.l10n_latam_manual_checks',
    )

    @api.depends('check_number')
    def _compute_l10n_latam_check_number(self):
        """ This dummy computed field is added for two reasons:
        1. add a new field so that we don't need to modify attrs on the views for the original check_number field
        (not nice on terms of inheritance)
        2. if we set it as related (with readonly=False) it didn't work properly for our use case: If the user changes
        the proposed number the value was not saved. This computed with inverse does the trick"""
        for rec in self:
            rec.l10n_latam_check_number = rec.check_number

    def _inverse_l10n_latam_check_number(self):
        for rec in self:
            rec.check_number = rec.l10n_latam_check_number

    def _compute_check_number(self):
        """ Override from account_check_printing.
        For electronic/deferred own checks or third party checks, don't call super so that number is not cleaned """
        latam_checks = self.filtered(
            lambda x: x.payment_method_line_id.code == 'new_third_party_checks' or
            (x.payment_method_line_id.code == 'check_printing' and x.l10n_latam_manual_checks))
        return super(AccountPayment, self - latam_checks)._compute_check_number()

    def _inverse_check_number(self):
        """ On third party checks or electronic/deferred own checks, avoid calling super because is not needed to write
        the sequence for these use case. """
        avoid_inverse = self.filtered(
            lambda x: x.l10n_latam_manual_checks or x.payment_method_line_id.code == 'new_third_party_checks')
        return super(AccountPayment, self - avoid_inverse)._inverse_check_number()

    @api.depends('payment_method_line_id.code', 'partner_id')
    def _compute_l10n_latam_check_bank_id(self):
        new_third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
        for rec in new_third_party_checks:
            rec.l10n_latam_check_bank_id = rec.partner_id.bank_ids[:1].bank_id
        (self - new_third_party_checks).l10n_latam_check_bank_id = False

    @api.depends('payment_method_line_id.code', 'partner_id')
    def _compute_l10n_latam_check_issuer_vat(self):
        new_third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
        for rec in new_third_party_checks:
            rec.l10n_latam_check_issuer_vat = rec.partner_id.vat
        (self - new_third_party_checks).l10n_latam_check_issuer_vat = False

    @api.onchange('l10n_latam_check_issuer_vat')
    def _clean_l10n_latam_check_issuer_vat(self):
        for rec in self.filtered('l10n_latam_check_issuer_vat'):
            stdnum_vat = stdnum.util.get_cc_module(rec.company_id.country_id.code, 'vat')
            if hasattr(stdnum_vat, 'compact'):
                rec.l10n_latam_check_issuer_vat = stdnum_vat.compact(rec.l10n_latam_check_issuer_vat)

    @api.constrains('l10n_latam_check_issuer_vat', 'company_id')
    def _check_l10n_latam_check_issuer_vat(self):
        for rec in self.filtered(lambda x: x.l10n_latam_check_issuer_vat and x.company_id.country_id):
            if not self.env['res.partner']._run_vat_test(rec.l10n_latam_check_issuer_vat, rec.company_id.country_id):
                error_message = self.env['res.partner']._build_vat_error_message(
                    rec.company_id.country_id.code.lower(), rec.l10n_latam_check_issuer_vat, 'Check Issuer VAT')
                raise ValidationError(error_message)

    @api.depends('payment_method_line_id', 'l10n_latam_check_issuer_vat', 'l10n_latam_check_bank_id', 'company_id',
                 'check_number', 'l10n_latam_check_id', 'state', 'date', 'is_internal_transfer')
    def _compute_l10n_latam_check_warning_msg(self):
        """ Compute warning message for latam checks checks """
        self.l10n_latam_check_warning_msg = False
        latam_draft_checks = self.filtered(
            lambda x: x.state == 'draft' and (x.l10n_latam_manual_checks or x.payment_method_line_id.code in [
                'in_third_party_checks', 'out_third_party_checks', 'new_third_party_checks']))
        for rec in latam_draft_checks:
            msgs = rec._get_blocking_l10n_latam_warning_msg()
            # moved third party check
            if rec.l10n_latam_check_id:
                date = rec.date or fields.Datetime.now()
                last_operation = rec.env['account.payment'].search([
                    ('state', '=', 'posted'),
                    '|', ('l10n_latam_check_id', '=', rec.l10n_latam_check_id.id),
                    ('id', '=', rec.l10n_latam_check_id.id),
                ], order="date desc, id desc", limit=1)
                if last_operation and last_operation[0].date > date:
                    msgs.append(_(
                        "It seems you're trying to move a check with a date (%s) prior to last operation done with "
                        "the check (%s). This may be wrong, please double check it. By continue, the last operation on "
                        "the check will remain being %s",
                        format_date(self.env, date), last_operation.display_name, last_operation.display_name))
            # new third party check
            elif rec.check_number and rec.payment_method_line_id.code == 'new_third_party_checks' and \
                    rec.l10n_latam_check_bank_id and rec.l10n_latam_check_issuer_vat:
                same_checks = self.search([
                    ('company_id', '=', rec.company_id.id),
                    ('l10n_latam_check_bank_id', '=', rec.l10n_latam_check_bank_id.id),
                    ('l10n_latam_check_issuer_vat', '=', rec.l10n_latam_check_issuer_vat),
                    ('check_number', '=', rec.check_number),
                    ('id', '!=', rec._origin.id)])
                if same_checks:
                    msgs.append(_(
                        "Other checks were found with same number, issuer and bank. Please double check you are not "
                        "encoding the same check more than once. List of other payments/checks: %s",
                        ", ".join(same_checks.mapped('display_name'))))
            rec.l10n_latam_check_warning_msg = msgs and '* %s' % '\n* '.join(msgs) or False

    def _get_blocking_l10n_latam_warning_msg(self):
        msgs = []
        for rec in self.filtered('l10n_latam_check_id'):
            if not rec.currency_id.is_zero(rec.l10n_latam_check_id.amount - rec.amount):
                msgs.append(_(
                    'The amount of the payment (%s) does not match the amount of the selected check (%s). '
                    'Please try to deselect and select the check again.', rec.amount, rec.l10n_latam_check_id.amount))
            if rec.payment_method_line_id.code in ['in_third_party_checks', 'out_third_party_checks']:
                if rec.l10n_latam_check_id.state != 'posted':
                    msgs.append(_('Selected check "%s" is not posted', rec.l10n_latam_check_id.display_name))
                elif (rec.payment_type == 'outbound' and
                        rec.l10n_latam_check_id.l10n_latam_check_current_journal_id != rec.journal_id) or (
                        rec.payment_type == 'inbound' and rec.is_internal_transfer and
                        rec.l10n_latam_check_id.l10n_latam_check_current_journal_id != rec.destination_journal_id):
                    # check outbound payment and transfer or inbound transfer
                    msgs.append(_(
                        'Check "%s" is not anymore in journal "%s", it seems it has been moved by another payment.',
                        rec.l10n_latam_check_id.display_name, rec.journal_id.name
                        if rec.payment_type == 'outbound' else rec.destination_journal_id.name))
                elif rec.payment_type == 'inbound' and not rec.is_internal_transfer and \
                        rec.l10n_latam_check_id.l10n_latam_check_current_journal_id:
                    msgs.append(_("Check '%s' is on journal '%s', it can't be received it again",
                                rec.l10n_latam_check_id.display_name, rec.journal_id.name))
        return msgs

    @api.depends('is_internal_transfer')
    def _compute_payment_method_line_fields(self):
        """ Add is_internal_transfer as a trigger to re-compute """
        return super()._compute_payment_method_line_fields()

    @api.depends('l10n_latam_check_operation_ids.state')
    def _compute_l10n_latam_check_current_journal(self):
        new_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
        payments = self.env['account.payment'].search(
            [('l10n_latam_check_id', 'in', new_checks.ids), ('state', '=', 'posted')], order="date desc, id desc")

        # we store on a dict the first payment (last operation) for each check
        checks_mapping = {}
        for payment in payments:
            if payment.l10n_latam_check_id not in checks_mapping:
                checks_mapping[payment.l10n_latam_check_id] = payment

        for rec in new_checks:
            last_operation = checks_mapping.get(rec)
            if not last_operation:
                rec.l10n_latam_check_current_journal_id = rec.journal_id
                continue
            if last_operation.is_internal_transfer and last_operation.payment_type == 'outbound':
                rec.l10n_latam_check_current_journal_id = last_operation.paired_internal_transfer_payment_id.journal_id
            elif last_operation.payment_type == 'inbound':
                rec.l10n_latam_check_current_journal_id = last_operation.journal_id
            else:
                rec.l10n_latam_check_current_journal_id = False

    @api.depends('l10n_latam_manual_checks')
    def _compute_show_check_number(self):
        latam_checks = self.filtered(
            lambda x: x.payment_method_line_id.code == 'new_third_party_checks' or
            (x.payment_method_line_id.code == 'check_printing' and x.l10n_latam_manual_checks))
        latam_checks.show_check_number = False
        super(AccountPayment, self - latam_checks)._compute_show_check_number()

    @api.constrains('check_number', 'journal_id')
    def _constrains_check_number(self):
        """ Don't enforce uniqueness for third party checks"""
        third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
        return super(AccountPayment, self - third_party_checks)._constrains_check_number()

    @api.onchange('l10n_latam_check_id')
    def _onchange_check(self):
        for rec in self.filtered('l10n_latam_check_id'):
            rec.amount = rec.l10n_latam_check_id.amount

    @api.onchange('payment_method_line_id', 'is_internal_transfer', 'journal_id', 'destination_journal_id')
    def _onchange_to_reset_check_ids(self):
        # If any of these fields change, the domain of the selectable checks could change
        self.l10n_latam_check_id = False

    @api.onchange('l10n_latam_check_number')
    def _onchange_check_number(self):
        for rec in self.filtered(
            lambda x: x.journal_id.company_id.country_id.code == "AR" and
            x.l10n_latam_check_number and x.l10n_latam_check_number.isdecimal()):
            rec.l10n_latam_check_number = '%08d' % int(rec.l10n_latam_check_number)

    def _get_payment_method_codes_to_exclude(self):
        res = super()._get_payment_method_codes_to_exclude()
        if self.is_internal_transfer:
            res.append('new_third_party_checks')
        return res

    def action_unmark_sent(self):
        """ Unmarking as sent for electronic/deferred check would give the option to print and re-number check but
        it's not implemented yet for this kind of checks"""
        if self.filtered(lambda x: x.payment_method_line_id.code == 'check_printing' and x.l10n_latam_manual_checks):
            raise UserError(_('Unmark sent is not implemented for electronic or deferred checks'))
        return super().action_unmark_sent()

    def action_post(self):
        msgs = self._get_blocking_l10n_latam_warning_msg()
        if msgs:
            raise ValidationError('* %s' % '\n* '.join(msgs))

        res = super().action_post()

        # mark own checks that are not printed as sent
        self.filtered(lambda x: x.payment_method_line_id.code == 'check_printing' and x.l10n_latam_manual_checks).write({'is_move_sent': True})
        return res

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ('l10n_latam_check_number',)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ Add check name and operation on liquidity line """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        check = self if (self.payment_method_line_id.code == 'new_third_party_checks' or (self.payment_method_line_id.code == 'check_printing' and self.l10n_latam_manual_checks)) \
            else self.l10n_latam_check_id
        if check:
            document_name = (_('Check %s received') if self.payment_type == 'inbound' else _('Check %s delivered')) % (
                check.check_number)
            res[0].update({
                'name': document_name + ' - ' + ''.join([item[1] for item in self._get_aml_default_display_name_list()]),
            })
        return res

    def name_get(self):
        """ Add check number to display_name on check_id m2o field """
        res_names = super().name_get()
        for i, (res_name, rec) in enumerate(zip(res_names, self)):
            if rec.check_number and rec.payment_method_line_id.code == 'new_third_party_checks':
                res_names[i] = (res_name[0], "%s %s" % (res_name[1], _("(Check %s)", rec.check_number)))
        return res_names

    def button_open_check_operations(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        operations = (self.l10n_latam_check_operation_ids.filtered(lambda x: x.state == 'posted') + self)
        action = {
            'name': _("Check Operations"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'views': [
                (self.env.ref('l10n_latam_check.view_account_third_party_check_operations_tree').id, 'tree'),
                (False, 'form')],
            'context': {'create': False},
            'domain': [('id', 'in', operations.ids)],
        }
        return action

    def _create_paired_internal_transfer_payment(self):
        """
        Two modifications when only when transferring from a third party checks journal:
        1. When a paired transfer is created, the default odoo behavior is to use on the paired transfer the first
        available payment method. If we are transferring to another third party checks journal, then set as payment
        method on the paired transfer 'in_third_party_checks' or 'out_third_party_checks'
        2. On the paired transfer set the l10n_latam_check_id field, this field is needed for the
        l10n_latam_check_operation_ids and also for some warnings and constrains.
        """
        third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code in [
            'in_third_party_checks',
            'out_third_party_checks'
        ])
        for rec in third_party_checks:
            dest_payment_method_code = 'in_third_party_checks' if rec.payment_type == 'outbound' else 'out_third_party_checks'
            dest_payment_method = rec.destination_journal_id.inbound_payment_method_line_ids.filtered(
                lambda x: x.code == dest_payment_method_code)
            if dest_payment_method:
                super(AccountPayment, rec.with_context(
                    default_payment_method_line_id=dest_payment_method.id,
                    default_l10n_latam_check_id=rec.l10n_latam_check_id,
                ))._create_paired_internal_transfer_payment()
            else:
                super(AccountPayment, rec.with_context(
                    default_l10n_latam_check_id=rec.l10n_latam_check_id,
                ))._create_paired_internal_transfer_payment()
        super(AccountPayment, self - third_party_checks)._create_paired_internal_transfer_payment()
