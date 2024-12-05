# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # EXTENDS sale
        self.expense_ids._sale_expense_reset_sol_quantities()
        return super()._reverse_moves(default_values_list, cancel)

    def button_draft(self):
        # EXTENDS sale
        self.expense_ids._sale_expense_reset_sol_quantities()
        return super().button_draft()

    def unlink(self):
        # EXTENDS sale
        self.expense_ids._sale_expense_reset_sol_quantities()
        return super().unlink()
