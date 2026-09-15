from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _reverse_moves(self, default_values_list=None, cancel=False):
        _debug.lifecycle("expense_reset_on_reverse", moves=self)
        self.expense_ids._sale_expense_reset_sol_quantities()
        return super()._reverse_moves(default_values_list, cancel)

    def action_draft(self):
        _debug.lifecycle("expense_reset_on_draft", moves=self)
        self.expense_ids._sale_expense_reset_sol_quantities()
        return super().action_draft()

    def unlink(self):
        _debug.lifecycle("expense_reset_on_unlink", moves=self)
        self.expense_ids._sale_expense_reset_sol_quantities()
        return super().unlink()
