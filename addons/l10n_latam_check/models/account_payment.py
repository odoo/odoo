from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    l10n_latam_check_id = fields.Many2one(
        'account.payment', string='Check', readonly=True,
        states={'draft': [('readonly', False)]}, copy=False)
    l10n_latam_check_current_journal_id = fields.Many2one(
        'account.journal', compute='_compute_l10n_latam_check_current_journal',
        string="Check Current Journal", store=True)
    l10n_latam_check_operation_ids = fields.One2many(
        'account.payment', 'l10n_latam_check_id', readonly=True, string='Check Operations')
    l10n_latam_check_bank_id = fields.Many2one(
        'res.bank', readonly=False, states={'cancel': [('readonly', True)], 'posted': [('readonly', True)]},
        compute='_compute_l10n_latam_check_data', store=True, string='Check Bank',)
    l10n_latam_check_issuer_vat = fields.Char(
        readonly=False, states={'cancel': [('readonly', True)], 'posted': [('readonly', True)]},
        compute='_compute_l10n_latam_check_data', store=True, string='Check Issuer VAT')
    l10n_latam_use_checkbooks = fields.Boolean(related='journal_id.l10n_latam_use_checkbooks')
    l10n_latam_checkbook_type = fields.Selection(related='l10n_latam_checkbook_id.type')
    l10n_latam_checkbook_id = fields.Many2one(
        'l10n_latam.checkbook', 'Checkbook', store=True,
        compute='_compute_l10n_latam_checkbook', readonly=True, states={'draft': [('readonly', False)]})
    l10n_latam_check_payment_date = fields.Date(
        string='Check Payment Date', readonly=True, states={'draft': [('readonly', False)]})
    l10n_latam_check_warning_msg = fields.Html(compute='_compute_l10n_latam_check_warning_msg')
    check_number = fields.Char(readonly=False)

    @api.depends('payment_method_line_id.code', 'journal_id.l10n_latam_use_checkbooks')
    def _compute_l10n_latam_checkbook(self):
        with_checkbooks = self.filtered(
            lambda x: x.payment_method_line_id.code == 'check_printing' and x.journal_id.l10n_latam_use_checkbooks)
        (self - with_checkbooks).l10n_latam_checkbook_id = False
        for rec in with_checkbooks:
            checkbooks = rec.journal_id.with_context(active_test=True).l10n_latam_checkbook_ids
            if rec.l10n_latam_checkbook_id and rec.l10n_latam_checkbook_id in checkbooks:
                continue
            rec.l10n_latam_checkbook_id = checkbooks and checkbooks[0] or False

    @api.depends('l10n_latam_checkbook_id')
    def _compute_check_number(self):
        no_print_checkbooks = self.filtered(lambda x: x.l10n_latam_checkbook_id)
        for pay in no_print_checkbooks:
            pay.check_number = pay.l10n_latam_checkbook_id.sequence_id.get_next_char(
                pay.l10n_latam_checkbook_id.next_number)
        return super(AccountPayment, self - no_print_checkbooks)._compute_check_number()

    def action_mark_sent(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        self.write({'is_move_sent': True})

    @api.onchange('l10n_latam_check_id')
    def _onchange_check(self):
        for rec in self.filtered('l10n_latam_check_id'):
            rec.amount = rec.l10n_latam_check_id.amount

    @api.depends('payment_method_line_id.code', 'partner_id')
    def _compute_l10n_latam_check_data(self):
        new_third_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        for rec in new_third_checks:
            rec.update({
                'l10n_latam_check_bank_id': rec.partner_id.bank_ids and rec.partner_id.bank_ids[0].bank_id or False,
                'l10n_latam_check_issuer_vat': rec.partner_id.vat,
            })

    @api.depends(
        'payment_method_line_id', 'l10n_latam_check_issuer_vat', 'l10n_latam_check_bank_id', 'company_id',
        'check_number', 'l10n_latam_check_id', 'state')
    def _compute_l10n_latam_check_warning_msg(self):
        self.l10n_latam_check_warning_msg = False
        for rec in self.filtered(lambda x: x.state == 'draft'):
            if rec.l10n_latam_check_id:
                date = rec.date or fields.Datetime.now()
                last_operation = rec.env['account.payment'].search([
                    ('state', '=', 'posted'), '|', ('l10n_latam_check_id', '=', rec.l10n_latam_check_id.id),
                    ('id', '=', rec.l10n_latam_check_id.id)], order="date desc, id desc", limit=1)
                if last_operation and last_operation[0].date > date:
                    rec.l10n_latam_check_warning_msg = _(
                        "It seems you're trying to move a check with a date (%s) prior to last operation done with "
                        "the check (%s). This may be wrong, please double check it. If continue, last operation on "
                        "the check will remain being %s") % (
                            format_date(self.env, date), last_operation.display_name, last_operation.display_name)
            elif rec.check_number and rec.payment_method_line_id.code == 'new_third_checks' and \
                    rec.l10n_latam_check_bank_id and rec.l10n_latam_check_issuer_vat:
                same_checks = self.search([
                    ('company_id', '=', rec.company_id.id),
                    ('l10n_latam_check_bank_id', '=', rec.l10n_latam_check_bank_id.id),
                    ('l10n_latam_check_issuer_vat', '=', rec.l10n_latam_check_issuer_vat),
                    ('check_number', '=', rec.check_number),
                    ('id', '!=', rec._origin.id)])
                if same_checks:
                    rec.l10n_latam_check_warning_msg = _(
                        "Other checks where found with same number, issuer and bank. Please double check you're not "
                        "encoding the same check more than once<br/>"
                        "List of other payments/checks: %s") % (",".join(same_checks.mapped('display_name')))

    @api.constrains('is_internal_transfer', 'payment_method_line_id')
    def _check_transfer(self):
        recs = self.filtered(lambda x: x.is_internal_transfer and x.payment_method_line_id.code == 'new_third_checks')
        if recs:
            raise UserError(_("You can't use New Third Checks on a transfer"))

    def action_post(self):
        # third checks validations
        for rec in self:
            if rec.l10n_latam_check_id and not rec.currency_id.is_zero(rec.l10n_latam_check_id.amount - rec.amount):
                raise UserError(_(
                    'The amount of the payment (%s) does not match the amount of the selected check (%s).\n'
                    'Please try to deselect and select check again.') % (rec.amount, rec.l10n_latam_check_id.amount))
            elif rec.payment_method_line_id.code in ['in_third_checks', 'out_third_checks']:
                if rec.l10n_latam_check_id.state != 'posted':
                    raise ValidationError(_('Selected check "%s" is not posted') % rec.l10n_latam_check_id.display_name)
                elif (
                        rec.payment_type == 'outbound' and
                        rec.l10n_latam_check_id.l10n_latam_check_current_journal_id != rec.journal_id) or (
                        rec.payment_type == 'inbound' and rec.is_internal_transfer and
                        rec.l10n_latam_check_current_journal_id != rec.destination_journal_id):
                    # check outbound payment and transfer or inbound transfer
                    raise ValidationError(_(
                        'Check "%s" is not anymore in journal "%s", it seems it has been moved by another payment.') % (
                            rec.l10n_latam_check_id.display_name, rec.journal_id.name
                            if rec.payment_type == 'outbound' else rec.destination_journal_id.name))
                elif rec.payment_type == 'inbound' and not rec.is_internal_transfer and \
                        rec.l10n_latam_check_current_journal_id:
                    raise ValidationError(_("Check '%s' is on journal '%s', we can't receive it again") % (
                        rec.l10n_latam_check_id.display_name, rec.journal_id.name))

        res = super().action_post()

        # mark own checks that are not printed as sent
        for rec in self.filtered(lambda x: x.check_number):
            sequence = rec.l10n_latam_checkbook_id.sequence_id
            sequence.sudo().write({'number_next_actual': int(rec.check_number) + 1})
            rec.write({'is_move_sent': True})
        return res

    @api.onchange('payment_method_line_id', 'is_internal_transfer', 'journal_id', 'destination_journal_id')
    def reset_check_ids(self):
        """ If any of this fields changes the domain of the selectable checks could change """
        self.l10n_latam_check_id = False

    @api.onchange('check_number')
    def _onchange_check_number(self):
        for rec in self.filtered(lambda x: x.journal_id.company_id.country_id.code == "AR"):
            try:
                if rec.check_number:
                    rec.check_number = '%08d' % int(rec.check_number)
            except Exception:
                pass

    @api.depends('l10n_latam_check_operation_ids.state')
    def _compute_l10n_latam_check_current_journal(self):
        new_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        for rec in new_checks:
            last_operation = rec.env['account.payment'].search(
                [('l10n_latam_check_id', '=', rec.id), ('state', '=', 'posted')], order="date desc, id desc", limit=1)
            if not last_operation:
                rec.l10n_latam_check_current_journal_id = rec.journal_id
                continue
            if last_operation.is_internal_transfer and last_operation.payment_type == 'outbound':
                rec.l10n_latam_check_current_journal_id = last_operation.paired_internal_transfer_payment_id.journal_id
            elif last_operation.is_internal_transfer and last_operation.payment_type == 'inbound':
                rec.l10n_latam_check_current_journal_id = last_operation.journal_id
            elif last_operation.payment_type == 'inbound':
                rec.l10n_latam_check_current_journal_id = last_operation.journal_id
            else:
                rec.l10n_latam_check_current_journal_id = False

    @api.model
    def _get_trigger_fields_to_sincronize(self):
        res = super()._get_trigger_fields_to_sincronize()
        return res + ('check_number',)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ Add check name and operation on liquidity line """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        check = self if self.payment_method_line_id.code == 'new_third_checks' else self.l10n_latam_check_id
        if check:
            document_name = (_('Check %s received') if self.payment_type == 'inbound' else _('Check %s delivered')) % (
                check.check_number)
            res[0].update({
                'name': self.env['account.move.line']._get_default_line_name(
                    document_name, self.amount, self.currency_id, self.date, partner=self.partner_id),
            })
            res[0].update({})
        return res

    def name_get(self):
        """ Add check number to display_name on check_id m2o field """
        res_names = super().name_get()
        for i, (res_name, rec) in enumerate(zip(res_names, self)):
            if rec.check_number:
                res_names[i] = (res_name[0], "%s %s" % (res_name[1], _("(Check %s)") % rec.check_number))
        return res_names

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """ Allow to search by check_number """
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            connector = '&' if operator in expression.NEGATIVE_TERM_OPERATORS else '|'
            domain = [connector, ('check_number', operator, name), ('name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

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
                (self.env.ref('l10n_latam_check.view_account_third_check_operations_tree').id, 'tree'),
                (False, 'form')],
            'context': {'create': False},
            'domain': [('id', 'in', operations.ids)],
        }
        return action

    def _create_paired_internal_transfer_payment(self):
        """
        1. On checks transfers, add check_id on paired transactions.
        2. If transfer to another checks journal choose 'check' payment mode on destination transfer
        """
        for rec in self.filtered(lambda x: x.payment_method_line_id.code in ['in_third_checks', 'out_third_checks']):
            dest_payment_method_code = 'in_third_checks' if rec.payment_type == 'outbound' else 'out_third_checks'
            dest_payment_method = rec.destination_journal_id.inbound_payment_method_line_ids.filtered(
                lambda x: x.code == dest_payment_method_code)
            if dest_payment_method:
                super(AccountPayment, rec.with_context(
                    default_payment_method_line_id=dest_payment_method.id,
                    default_check_id=rec.l10n_latam_check_id))._create_paired_internal_transfer_payment()
            else:
                super(AccountPayment, rec.with_context(
                    default_check_id=rec.l10n_latam_check_id))._create_paired_internal_transfer_payment()
            self -= rec
        super(AccountPayment, self)._create_paired_internal_transfer_payment()
