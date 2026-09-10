from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _eligible_for_stock_account(self):
        if super()._eligible_for_stock_account():
            return True
        dropshipped_moves = self._get_stock_moves().filtered(lambda m: m._is_dropshipped())
        return bool(
            self.product_id.is_storable
            and dropshipped_moves
            and all(m._is_resupply_dropship() for m in dropshipped_moves)
        )
