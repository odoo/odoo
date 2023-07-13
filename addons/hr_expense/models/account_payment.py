# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import escape

from odoo import models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

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
        super()._synchronize_from_moves(changed_fields)

    def _synchronize_to_moves(self, changed_fields):
        # EXTENDS account
        if self.expense_sheet_id:
            raise UserError(_("You cannot do this modification since the payment is linked to an expense report."))
        return super()._synchronize_to_moves(changed_fields)

    def _creation_message(self):
        # EXTENDS mail
        self.ensure_one()
        if self.move_id.expense_sheet_id:
            return escape(_("Payment created for: %s")) % self.move_id.expense_sheet_id._get_html_link()
        return super()._creation_message()

    def unlink(self):
        # EXTENDS account
        if self.expense_sheet_id and self.expense_sheet_id.account_move_ids.payment_ids - self:  # If not all the payments are to be deleted
            raise UserError(_("You cannot delete only some payments linked to an expense report. All payments must be deleted at the same time."))
        return super().unlink()
