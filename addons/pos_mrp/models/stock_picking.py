from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_lot_line_qty(self, line, move, lines_data):
        qty = super()._get_lot_line_qty(line, move, lines_data)
        if move.bom_line_id:
            bom = move.bom_line_id.bom_id
            if bom.product_id:
                kit_data = lines_data.get(bom.product_id.id, {})
            else:
                kit_data = {}
                for data in lines_data.values():
                    if data.get('order_lines') and data['order_lines'].product_id.product_tmpl_id == bom.product_tmpl_id:
                        kit_data = data
                        break
            if kit_data.get('order_lines'):
                qty = sum(kit_data['order_lines'].mapped("qty")) * move.bom_line_id.product_qty
        return qty
