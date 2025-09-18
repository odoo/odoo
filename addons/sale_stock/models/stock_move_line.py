from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # ------------------------------------------------------------
    # VALIDATIONS
    # ------------------------------------------------------------

    def _should_show_lot_in_invoice(self):
        """Check if lot should be shown in invoice for customer movements.

        This method can be extended by other modules (e.g., purchase_stock)
        to add additional conditions.
        """
        # Call parent implementation if it exists (e.g., from purchase_stock)
        try:
            res = super()._should_show_lot_in_invoice()
        except AttributeError:
            res = False
        return res or "customer" in {
            self.location_id.usage,
            self.location_dest_id.usage,
        } or self.env.ref("stock.stock_location_inter_company") in (
            self.location_id,
            self.location_dest_id,
        )
