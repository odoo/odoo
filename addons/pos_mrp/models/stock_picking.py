from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_lot_line_qty(self, line, move, lines_data):
        qty = super()._get_lot_line_qty(line, move, lines_data)
        if move.bom_line_id:
            kit_product_id = move.bom_line_id.bom_id.product_tmpl_id.product_variant_id.id
            kit_lines = line.order_id.lines.filtered(lambda l: l.product_id.id == kit_product_id)
            qty = sum(kit_lines.mapped('qty')) * move.bom_line_id.product_qty
        return qty
