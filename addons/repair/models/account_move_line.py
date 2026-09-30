from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _eligible_for_stock_account(self):
        moves = self._get_stock_moves()
        already_accounted = any(m.repair_id and m.account_move_id for m in moves.filtered(lambda m: m.repair_line_type == 'add'))
        return super()._eligible_for_stock_account() and not already_accounted
