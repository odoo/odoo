from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _should_show_lot_in_invoice(self):
        """Check if lot should be shown in invoice for supplier movements.

        This extends the method from sale_stock (if installed) to also show
        lots for supplier locations (purchase receipts/returns).
        """
        # Call parent implementation if it exists (e.g., from sale_stock)
        try:
            res = super()._should_show_lot_in_invoice()
        except AttributeError:
            res = False
        return res or "supplier" in {
            self.location_id.usage,
            self.location_dest_id.usage,
        } or self.env.ref("stock.stock_location_inter_company") in (
            self.location_id,
            self.location_dest_id,
        )
