import stdnum

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_latam_check_ids = fields.Many2many(
        comodel_name='l10n_latam.account.payment.check',
        relation='account_payment_account_payment_check_rel',
        column1="payment_id",
        column2="check_id",
        required=True,
        string="Checks"
    )

    # This is a technical field for the view only
    l10n_latam_manual_checks = fields.Boolean(
        related='journal_id.l10n_latam_manual_checks',
    )
    amount = fields.Monetary(compute="_compute_amount", readonly=False)

    @api.depends('l10n_latam_check_ids.amount')
    def _compute_amount(self):
        for rec in self.filtered('l10n_latam_check_ids'):
            rec.amount = sum(self.l10n_latam_check_ids.mapped('amount'))

    # @api.depends('payment_method_line_id', 'l10n_latam_check_issuer_vat', 'l10n_latam_check_bank_id', 'company_id',
    #              'l10n_latam_check_number', 'l10n_latam_check_id', 'state', 'date', 'is_internal_transfer', 'amount', 'currency_id')
    # def _compute_l10n_latam_check_warning_msg(self):
    #     """
    #     Compute warning message for latam checks checks
    #     We use l10n_latam_check_number as de dependency because on the interface this is the field the user is using.
    #     Another approach could be to add an onchange on _inverse_l10n_latam_check_number method
    #     """
    #     self.l10n_latam_check_warning_msg = False
    #     latam_draft_checks = self.filtered(
    #         lambda x: x.state == 'draft' and (x.l10n_latam_manual_checks or x.payment_method_line_id.code in [
    #             'in_third_party_checks', 'out_third_party_checks', 'new_third_party_checks']))
    #     for rec in latam_draft_checks:
    #         msgs = rec._get_blocking_l10n_latam_warning_msg()
    #         # new third party check
    #         if rec.l10n_latam_check_number and rec.payment_method_line_id.code == 'new_third_party_checks' and \
    #                 rec.l10n_latam_check_bank_id and rec.l10n_latam_check_issuer_vat:
    #             same_checks = self.search([
    #                 ('company_id', '=', rec.company_id.id),
    #                 ('l10n_latam_check_bank_id', '=', rec.l10n_latam_check_bank_id.id),
    #                 ('l10n_latam_check_issuer_vat', '=', rec.l10n_latam_check_issuer_vat),
    #                 ('check_number', '=', rec.l10n_latam_check_number),
    #                 ('id', '!=', rec._origin.id)])
    #             if same_checks:
    #                 msgs.append(_(
    #                     "Other checks were found with same number, issuer and bank. Please double check you are not "
    #                     "encoding the same check more than once. List of other payments/checks: %s",
    #                     ", ".join(same_checks.mapped('display_name'))))
    #         rec.l10n_latam_check_warning_msg = msgs and '* %s' % '\n* '.join(msgs) or False

    # def _get_blocking_l10n_latam_warning_msg(self):
    #     msgs = []
    #     for rec in self.filtered('l10n_latam_check_id'):
    #         if rec.currency_id != rec.l10n_latam_check_id.currency_id:
    #             msgs.append(_(
    #                 'The currency of the payment (%s) and the currency of the check (%s) must be the same.') % (
    #                     rec.currency_id.name, rec.l10n_latam_check_id.currency_id.name))
    #         if not rec.currency_id.is_zero(rec.l10n_latam_check_id.amount - rec.amount):
    #             msgs.append(_(
    #                 'The amount of the payment (%s) does not match the amount of the selected check (%s). '
    #                 'Please try to deselect and select the check again.', rec.amount, rec.l10n_latam_check_id.amount))
    #         if rec.payment_method_line_id.code in ['in_third_party_checks', 'out_third_party_checks']:
    #             if rec.l10n_latam_check_id.state != 'posted':
    #                 msgs.append(_('Selected check "%s" is not posted', rec.l10n_latam_check_id.display_name))
    #             elif (rec.payment_type == 'outbound' and
    #                     rec.l10n_latam_check_id.l10n_latam_check_current_journal_id != rec.journal_id) or (
    #                     rec.payment_type == 'inbound' and rec.is_internal_transfer and
    #                     rec.l10n_latam_check_id.l10n_latam_check_current_journal_id != rec.destination_journal_id):
    #                 # check outbound payment and transfer or inbound transfer
    #                 msgs.append(_(
    #                     'Check "%s" is not anymore in journal "%s", it seems it has been moved by another payment.',
    #                     rec.l10n_latam_check_id.display_name, rec.journal_id.name
    #                     if rec.payment_type == 'outbound' else rec.destination_journal_id.name))
    #             elif rec.payment_type == 'inbound' and not rec.is_internal_transfer and \
    #                     rec.l10n_latam_check_id.l10n_latam_check_current_journal_id:
    #                 msgs.append(_("Check '%s' is on journal '%s', it can't be received it again",
    #                             rec.l10n_latam_check_id.display_name, rec.journal_id.name))
    #         # moved third party check
    #         if rec.l10n_latam_check_id:
    #             date = rec.date or fields.Datetime.now()
    #             last_operation = rec.env['account.payment'].search([
    #                 ('state', '=', 'posted'),
    #                 '|', ('l10n_latam_check_id', '=', rec.l10n_latam_check_id.id),
    #                 ('id', '=', rec.l10n_latam_check_id.id),
    #             ], order="date desc, id desc", limit=1)
    #             if last_operation and last_operation[0].date > date:
    #                 msgs.append(_(
    #                     "It seems you're trying to move a check with a date (%s) prior to last operation done with "
    #                     "the check (%s). This may be wrong, please double check it. By continue, the last operation on "
    #                     "the check will remain being %s",
    #                     format_date(self.env, date), last_operation.display_name, last_operation.display_name))
    #     return msgs

    @api.depends('is_internal_transfer')
    def _compute_payment_method_line_fields(self):
        """ Add is_internal_transfer as a trigger to re-compute """
        return super()._compute_payment_method_line_fields()

    # @api.depends('l10n_latam_manual_checks')
    # def _compute_show_check_number(self):
    #     latam_checks = self.filtered(
    #         lambda x: x.payment_method_line_id.code == 'new_third_party_checks' or
    #         (x.payment_method_line_id.code == 'check_printing' and x.l10n_latam_manual_checks))
    #     latam_checks.show_check_number = False
    #     super(AccountPayment, self - latam_checks)._compute_show_check_number()

    # @api.constrains('check_number', 'journal_id')
    # def _constrains_check_number_unique(self):
    #     """ Don't enforce uniqueness for third party checks"""
    #     third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
    #     return super(AccountPayment, self - third_party_checks)._constrains_check_number_unique()

    # @api.onchange('l10n_latam_check_id')
    # def _onchange_check(self):
    #     for rec in self.filtered('l10n_latam_check_id'):
    #         rec.amount = rec.l10n_latam_check_id.amount

    # @api.onchange('payment_method_line_id', 'is_internal_transfer', 'journal_id', 'destination_journal_id')
    # def _onchange_to_reset_check_ids(self):
    #     # If any of these fields change, the domain of the selectable checks could change
    #     self.l10n_latam_check_id = False

    # @api.onchange('l10n_latam_check_number')
    # def _onchange_check_number(self):
    #     for rec in self.filtered(
    #         lambda x: x.journal_id.company_id.country_id.code == "AR" and
    #         x.l10n_latam_check_number and x.l10n_latam_check_number.isdecimal()):
    #         rec.l10n_latam_check_number = '%08d' % int(rec.l10n_latam_check_number)

    def _get_payment_method_codes_to_exclude(self):
        res = super()._get_payment_method_codes_to_exclude()
        if self.is_internal_transfer:
            res.append('new_third_party_checks')
        return res

    # def action_unmark_sent(self):
    #     """ Unmarking as sent for electronic/deferred check would give the option to print and re-number check but
    #     it's not implemented yet for this kind of checks"""
    #     if self.filtered(lambda x: x.payment_method_line_id.code == 'check_printing' and x.l10n_latam_manual_checks):
    #         raise UserError(_('Unmark sent is not implemented for electronic or deferred checks'))
    #     return super().action_unmark_sent()

    # def action_post(self):
    #     msgs = self._get_blocking_l10n_latam_warning_msg()
    #     if msgs:
    #         raise ValidationError('* %s' % '\n* '.join(msgs))

    #     res = super().action_post()

    #     # mark own checks that are not printed as sent
    #     self.filtered(lambda x: x.payment_method_line_id.code == 'check_printing' and x.l10n_latam_manual_checks).write({'is_move_sent': True})
    #     return res

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ('l10n_latam_check_ids',)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ Add check name and operation on liquidity line """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        # check = self if (self.payment_method_line_id.code == 'new_third_party_checks' or (self.payment_method_line_id.code == 'own_printing' and self.l10n_latam_manual_checks)) \
        #     else self.l10n_latam_check_id
        if self.l10n_latam_check_ids:
            document_names = (_('Check %s received') if self.payment_type == 'inbound' else _('Check %s delivered')) % (
                     ', '.join(self.l10n_latam_check_ids.mapped('name')))
            res[0].update({
                'name': document_names + ' - ' + ''.join([item[1] for item in self._get_aml_default_display_name_list()]),
            })
        return res

    # @api.depends('check_number', 'payment_method_line_id')
    # def _compute_display_name(self):
    #     """ Add check number to display_name on check_id m2o field """
    #     super()._compute_display_name()
    #     for rec in self:
    #         if rec.check_number and rec.payment_method_line_id.code == 'new_third_party_checks':
    #             rec.display_name = "{} {}".format(rec.display_name, _("(Check %s)", rec.check_number))

    # def _create_paired_internal_transfer_payment(self):
    #     """
    #     Two modifications when only when transferring from a third party checks journal:
    #     1. When a paired transfer is created, the default odoo behavior is to use on the paired transfer the first
    #     available payment method. If we are transferring to another third party checks journal, then set as payment
    #     method on the paired transfer 'in_third_party_checks' or 'out_third_party_checks'
    #     2. On the paired transfer set the l10n_latam_check_id field, this field is needed for the
    #     l10n_latam_check_operation_ids and also for some warnings and constrains.
    #     """
    #     third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code in [
    #         'in_third_party_checks',
    #         'out_third_party_checks'
    #     ])
    #     for rec in third_party_checks:
    #         dest_payment_method_code = 'in_third_party_checks' if rec.payment_type == 'outbound' else 'out_third_party_checks'
    #         dest_payment_method = rec.destination_journal_id.inbound_payment_method_line_ids.filtered(
    #             lambda x: x.code == dest_payment_method_code)
    #         if dest_payment_method:
    #             super(AccountPayment, rec.with_context(
    #                 default_payment_method_line_id=dest_payment_method.id,
    #                 default_l10n_latam_check_id=rec.l10n_latam_check_id,
    #             ))._create_paired_internal_transfer_payment()
    #         else:
    #             super(AccountPayment, rec.with_context(
    #                 default_l10n_latam_check_id=rec.l10n_latam_check_id,
    #             ))._create_paired_internal_transfer_payment()
    #     super(AccountPayment, self - third_party_checks)._create_paired_internal_transfer_payment()

    # @api.constrains('l10n_latam_check_id')
    # def _check_l10n_latam_check_id(self):
    #     if self.filtered(lambda x: x.payment_method_line_id.code == 'out_third_party_checks'):
    #         payments = self.env['account.payment'].search_count([
    #             ('l10n_latam_check_id', 'in', self.l10n_latam_check_id.ids),
    #             ('payment_type', '=', 'outbound'),
    #             ('journal_id', 'in', self.journal_id.ids),
    #             ('id', 'not in', self.ids)],
    #             limit=1)
    #         if payments:
    #             raise ValidationError(_(
    #                 "The check(s) '%s' is already used on another payment. Please select another check or "
    #                 "deselect the check on this payment.", self.l10n_latam_check_id.mapped('display_name')))
