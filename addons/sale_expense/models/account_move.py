# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        # EXTENDS account
        # The order to reinvoice may be set on an expense that is already approved (its
        # journal entry exists but not posted). That entry was prepared without an
        # analytic distribution, so the expense would never be reinvoiced.
        # Sync the distribution of such expenses on their entry before posting it.
        if expenses := self.sudo().expense_ids.filtered('sale_order_id'):
            expenses._sale_expense_ensure_analytic_distribution()
            lines = self.sudo().line_ids.filtered(
                lambda line: line.expense_id in expenses
                and line.display_type == 'product'
                and not line.analytic_distribution
            )
            for line in lines:
                line.analytic_distribution = line.expense_id.analytic_distribution
        return super()._post(soft=soft)

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
