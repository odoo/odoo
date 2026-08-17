from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _adapt_kit_lot(self, move_lines_to_create, taken_qty_by_quant):
        if self._should_track_kit_product():
            qty = self.product_uom_qty
            quants = self.env['stock.quant']._gather(self.product_id, self.location_id, strict=False)
            quants = quants.filtered(lambda q: q.lot_id and q.quantity > 0.0)
            fallback_lot = quants[0].lot_id if quants else self.env['stock.lot'].search([('product_id', '=', self.product_id.id)], limit=1)
            move_lines_to_create.extend(self._get_ml_vals(self, qty, quants, taken_qty_by_quant, fallback_lot))
            return True
        return super()._adapt_kit_lot(move_lines_to_create, taken_qty_by_quant)

    def _should_track_kit_product(self):
        return super()._should_track_kit_product() or self.bom_line_id and self.product_id.tracking != 'none'
