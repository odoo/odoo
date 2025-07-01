# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.api import ondelete
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    expense_sheet_id = fields.Many2one(related='move_id.expense_sheet_id')

    def _compute_outstanding_account_id(self):
        # EXTENDS account
        expense_company_payments = self.filtered(lambda payment: payment.expense_sheet_id.payment_mode == 'company_account')
        for payment in expense_company_payments:
            payment.outstanding_account_id = payment.expense_sheet_id._get_expense_account_destination()
        super(AccountPayment, self - expense_company_payments)._compute_outstanding_account_id()

    def write(self, vals):
        trigger_fields = {
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id'
            'ref', 'expense_sheet_id', 'payment_method_line_id'
        }
        if self.expense_sheet_id and any(field_name in trigger_fields for field_name in vals):
            raise UserError(_("You cannot do this modification since the payment is linked to an expense report."))
        return super().write(vals)

    def action_open_expense_report(self):
        self.ensure_one()
        return {
            'name': self.expense_sheet_id.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'hr.expense.sheet',
            'res_id': self.expense_sheet_id.id
        }

    def _creation_message(self):
        # EXTENDS mail
        self.ensure_one()
        if self.move_id.expense_sheet_id:
            return _("Payment created for: %s", self.move_id.expense_sheet_id._get_html_link())
        return super()._creation_message()

    @ondelete(at_uninstall=True)
    def _must_delete_all_expense_payments(self):
        if self.expense_sheet_id and self.expense_sheet_id.account_move_ids.payment_ids - self:  # If not all the payments are to be deleted
            raise UserError(_("You cannot delete only some payments linked to an expense report. All payments must be deleted at the same time."))
