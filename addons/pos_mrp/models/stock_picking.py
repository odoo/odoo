from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_lot_line_qty(self, line, move, lines_data):
        qty = super()._get_lot_line_qty(line, move, lines_data)
        if move.bom_line_id:
            qty = lines_data[move.bom_line_id.bom_id.product_tmpl_id.product_variant_id.id]['order_lines'].qty * move.bom_line_id.product_qty
        return qty
