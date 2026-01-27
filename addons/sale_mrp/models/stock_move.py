# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        order_line = self.sale_line_id
        if order_line and all(move.sale_line_id == order_line for move in self) and any(move.product_id != order_line.product_id for move in self):
            product = order_line.product_id.with_company(order_line.company_id)
            bom = product.env['mrp.bom']._bom_find(product, company_id=self.company_id.id, bom_type='phantom')[product]
            if bom:
                return self._get_kit_price_unit(product, bom, order_line.qty_delivered)
        return super()._get_price_unit()
