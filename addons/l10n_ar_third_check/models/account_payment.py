from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    check_id = fields.Many2one('account.payment', string='Check', readonly=True, states={'draft': [('readonly', False)]}, copy=False,)
    third_check_current_journal_id = fields.Many2one('account.journal', compute='_compute_third_check_last_journal', string="Third Check Current Journal", store=True)
    third_check_operation_ids = fields.One2many('account.payment', 'check_id', readonly=True)
    third_check_bank_id = fields.Many2one(
        'res.bank', readonly=False, states={'cancel': [('readonly', True)], 'posted': [('readonly', True)]},
        compute='_compute_third_check_data', store=True,
    )
    third_check_issuer_vat = fields.Char(
        readonly=False, states={'cancel': [('readonly', True)], 'posted': [('readonly', True)]},
        compute='_compute_third_check_data', store=True,
    )

    @api.onchange('check_id')
    def _onchange_check(self):
        for rec in self.filtered('check_id'):
            rec.amount = rec.check_id.amount

    @api.depends('payment_method_line_id.code', 'partner_id')
    def _compute_third_check_data(self):
        new_third_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        for rec in new_third_checks:
            rec.update({
                'third_check_bank_id': rec.partner_id.bank_ids and rec.partner_id.bank_ids[0].bank_id or False,
                'third_check_issuer_vat': rec.partner_id.vat,
            })

    @api.constrains('is_internal_transfer', 'payment_method_line_id')
    def _check_transfer(self):
        recs = self.filtered(lambda x: x.is_internal_transfer and x.payment_method_line_id.code == 'new_third_checks')
        if recs:
            raise UserError(_("You can't use New Third Checks on a transfer"))

    @api.constrains('payment_method_line_id', 'third_check_issuer_vat', 'third_check_bank_id', 'company_id', 'check_number')
    def _check_unique(self):
        for rec in self.filtered(lambda x: x.check_number and x.payment_method_line_id.code == 'new_third_checks'):
            same_checks = self.search([
                ('company_id', '=', rec.company_id.id),
                ('third_check_bank_id', '=', rec.third_check_bank_id.id),
                ('third_check_issuer_vat', '=', rec.third_check_issuer_vat),
                ('check_number', '=', rec.check_number),
            ])
            same_checks -= rec
            if same_checks:
                raise UserError(_(
                    'Check Number (%s) must be unique per Owner and Bank!'
                    '\n* Check ids: %s') % (rec.check_number, same_checks.ids))

    @api.constrains('check_id')
    def _check_amount_and_date(self):
        for rec in self.filtered('check_id'):
            date = self.date or fields.Datetime.now()
            last_operation = rec.env['account.payment'].search(
                [('check_id', '=', rec.id), ('state', '=', 'posted')], order="date desc, id desc, name desc", limit=1)
            if last_operation and last_operation[0].date > date:
                raise ValidationError(_(
                    'The date of a new check operation can not be minor than last operation date.\n'
                    '* Check Id: %s\n'
                    '* Check Number: %s\n'
                    '* Operation Date: %s\n'
                    '* Last Operation Date: %s') % (
                        rec.check_id.id, rec.check_id.check_number, date, last_operation.date))

        for rec in self.filtered('check_id'):
            if not rec.currency_id.is_zero(rec.check_id.amount - rec.amount):
                raise UserError(_(
                    'The amount of the payment (%s) does not match the amount of the selected check (%s).\n'
                    'Please try to deselect and select check again.') % (rec.amount, rec.check_id.amount))

    @api.onchange('payment_method_line_id', 'is_internal_transfer', 'journal_id', 'destination_journal_id')
    def reset_check_ids(self):
        """ If any of this fields changes the domain of the selectable checks could change """
        self.check_id = False

    @api.onchange('check_number')
    def _onchange_check_number(self):
        for rec in self.filtered(lambda x: x.journal_id.company_id.country_id.code == "AR"):
            try:
                if rec.check_number:
                    rec.check_number = '%08d' % int(rec.check_number)
            except Exception:
                pass

    @api.depends('third_check_operation_ids.journal_id', 'third_check_operation_ids.state', 'payment_method_line_id')
    def _compute_third_check_last_journal(self):
        new_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        for rec in new_checks:
            last_operation = rec.env['account.payment'].search(
                [('check_id', '=', rec.id), ('state', '=', 'posted')], order="date desc, id desc, name desc", limit=1)
            if not last_operation:
                rec.third_check_current_journal_id = rec.journal_id
                continue
            if last_operation.is_internal_transfer and last_operation.payment_type == 'outbound':
                rec.third_check_current_journal_id = last_operation.paired_internal_transfer_payment_id.journal_id
            elif last_operation.is_internal_transfer and last_operation.payment_type == 'inbound':
                rec.third_check_current_journal_id = last_operation.journal_id
            elif last_operation.payment_type == 'inbound':
                rec.third_check_current_journal_id = last_operation.journal_id
            else:
                rec.third_check_current_journal_id = False

    @api.model
    def _get_trigger_fields_to_sincronize(self):
        res = super()._get_trigger_fields_to_sincronize()
        return res + ('check_number',)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ Add check name and operation on liquidity line """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        check = self if self.payment_method_line_id.code == 'new_third_checks' else self.check_id
        if check:
            document_name = (_('Check %s received') if self.payment_type == 'inbound' else _('Check %s delivered')) % (
                check.check_number)
            res[0].update({
                'name': self.env['account.move.line']._get_default_line_name(
                    document_name, self.amount, self.currency_id, self.date, partner=self.partner_id),
            })
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

        action = {
            'name': _("Check Operations"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'views': [
                (self.env.ref('l10n_ar_third_check.view_account_third_check_operations_tree').id, 'tree'),
                (False, 'form')],
            'context': {'create': False},
            'domain': [('id', 'in', (self.third_check_operation_ids.filtered(lambda x: x.state == 'posted') + self).ids)],
        }
        return action

    def _create_paired_internal_transfer_payment(self):
        """
        1. On checks transfers, add check_id on paired transactions.
        2. If transfer to another checks journal choose 'check' payment mode on destination transfer
        """
        for rec in self.filtered(lambda x: x.payment_method_line_id.code in ['in_third_checks', 'out_third_checks']):
            destionation_payment_method_code = 'in_third_checks' if rec.payment_type == 'outbound' else 'out_third_checks'
            destination_payment_method = rec.destination_journal_id.inbound_payment_method_line_ids.filtered(
                lambda x: x.code == destionation_payment_method_code)
            if destination_payment_method:
                super(AccountPayment, rec.with_context(
                    default_check_id=rec.check_id, default_payment_method_line_id=destination_payment_method.id))._create_paired_internal_transfer_payment()
            else:
                super(AccountPayment, rec.with_context(default_check_id=rec.check_id))._create_paired_internal_transfer_payment()
            self -= rec
        super(AccountPayment, self)._create_paired_internal_transfer_payment()
