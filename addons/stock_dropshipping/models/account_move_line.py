from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _use_inventory_valuation(self):
        # EXTENDS 'account': dropshipped (or, via `repair`, already-accounted) lines never touch stock.
        self.ensure_one()
        if not super()._use_inventory_valuation():
            return False
        return all(not m._is_dropshipped() for m in (self.sale_line_ids.move_ids | self.purchase_line_id.move_ids))
