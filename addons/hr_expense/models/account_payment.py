# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_cancel(self):
        # EXTENDS account
        for payment in self:
            if payment.expense_sheet_id:
                payment = payment.with_context(skip_account_move_synchronization=True)
                paid_by_employee = payment.expense_sheet_id.payment_mode == 'own_account'
                payment.expense_sheet_id.state = 'post' if paid_by_employee else 'approve'
                payment.expense_sheet_id = False

        return super().action_cancel()

    def action_draft(self):
        if self.reconciled_bill_ids.expense_sheet_id:
            self.reconciled_bill_ids.expense_sheet_id.write({'state': 'post'})
        return super().action_draft()

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

    def _synchronize_from_moves(self, changed_fields):
        # EXTENDS account
        if self.expense_sheet_id:
            # Constraints bypass when entry is linked to an expense.
            # Context is not enough, as we want to be able to delete
            # and update those entries later on.
            return
        return super()._synchronize_from_moves(changed_fields)

    def _synchronize_to_moves(self, changed_fields):
        # EXTENDS account
        if self.expense_sheet_id:
            raise UserError(_("You cannot do this modification since the payment is linked to an expense report."))
        return super()._synchronize_to_moves(changed_fields)

    def _creation_message(self):
        # EXTENDS mail
        self.ensure_one()
        if self.move_id.expense_sheet_id:
            return _("Payment created for: %s", self.move_id.expense_sheet_id._get_html_link())
        return super()._creation_message()
