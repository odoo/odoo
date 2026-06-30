# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        pos_order_line_id = self.env.context.get('pos_order_line_id')
        bom_id = self.env.context.get('bom_id')
        if not pos_order_line_id or not bom_id:
            return super()._get_price_unit()
        pos_order_line = self.env['pos.order.line'].browse(pos_order_line_id)
        bom = self.env['mrp.bom'].browse(bom_id)
        if pos_order_line and bom:
            return self._get_kit_price_unit(pos_order_line.product_id, bom, pos_order_line.qty)
        return super()._get_price_unit()
