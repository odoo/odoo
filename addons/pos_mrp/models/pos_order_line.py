# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def _get_stock_moves_to_consider(self, stock_moves, product):
        self.ensure_one()
        bom = product.env['mrp.bom']._bom_find(product, company_id=stock_moves.company_id.id, bom_type='phantom').get(product)
        if not bom:
            return super()._get_stock_moves_to_consider(stock_moves, product)
        boms, components = bom.explode(product, self.qty)
        # Get a flat list of all bom_line_ids
        bom_line_ids = [item.id for x in boms for item in x[0].bom_line_ids if set(item.bom_product_template_attribute_value_ids.ids).issubset(product.product_template_variant_value_ids.ids)]
        ml_product_to_consider = (product.bom_ids and [comp[0].product_id.id for comp in components]) or [product.id]
        return stock_moves.filtered(lambda ml: ml.product_id.id in ml_product_to_consider and (ml.bom_line_id.id in bom_line_ids))
