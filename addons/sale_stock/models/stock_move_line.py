
from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # ------------------------------------------------------------
    # VALIDATIONS
    # ------------------------------------------------------------

    def _should_show_lot_in_invoice(self):
        return "customer" in {
            self.location_id.usage,
            self.location_dest_id.usage,
        } or self.env.ref("stock.stock_location_inter_company") in (
            self.location_id,
            self.location_dest_id,
        )
