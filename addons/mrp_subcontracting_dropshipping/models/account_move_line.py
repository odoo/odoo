from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _use_inventory_valuation(self):
        dropshipped_moves = self.cogs_move_ids.filtered(lambda m: m._is_dropshipped())
        eligible_for_resupply_dropship = bool(
            self.product_id.is_storable
            and dropshipped_moves
            and all(m._is_resupply_dropship() for m in dropshipped_moves)
        )
        return super()._use_inventory_valuation() or eligible_for_resupply_dropship
