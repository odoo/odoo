# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_price_unit(self):
        """ Returns the unit price to value this stock move """
        line = self.env.context.get('pos_order_line')
        if line:
            product = line.product_id.with_company(self.company_id)
            bom = product.env['mrp.bom']._bom_find(product, company_id=self.company_id.id, bom_type='phantom')[product]
            if bom:
                return self._get_kit_price_unit(product, bom, line.qty)
        return super()._get_price_unit()
