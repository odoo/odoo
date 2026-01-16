# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    expense_ids = fields.One2many(related='move_id.expense_ids')

    def _compute_outstanding_account_id(self):
        # EXTENDS account
        expense_company_payments = self.filtered(lambda payment: payment.expense_ids.payment_mode == 'company_account')
        for payment in expense_company_payments:
            payment.outstanding_account_id = payment.expense_ids._get_expense_account_destination()
        super(AccountPayment, self - expense_company_payments)._compute_outstanding_account_id()

    def _compute_show_require_partner_bank(self):
        expense_payments = self.filtered(lambda pay: pay.move_id.expense_ids)
        super()._compute_show_require_partner_bank()
        expense_payments.require_partner_bank_account = False

    def write(self, vals):
        trigger_fields = {
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id'
            'ref', 'payment_method_line_id'
        }
        if self.expense_ids and any(field_name in trigger_fields for field_name in vals):
            raise UserError(_("You cannot do this modification since the payment is linked to an expense."))
        return super().write(vals)

    def action_open_expense(self):
        self.ensure_one()
        return {
            'name': self.expense_ids.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'hr.expense',
            'res_id': self.expense_ids.id,
        }

    def _creation_message(self):
        # EXTENDS mail
        self.ensure_one()
        if self.move_id.expense_ids:
            return _("Payment created for: %s", self.move_id.expense_ids._get_html_link())
        return super()._creation_message()

