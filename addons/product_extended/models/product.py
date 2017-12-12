# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    @api.multi
    def compute_price(self):
        for template in self:
            if template.product_variant_count == 1:
                return template.product_variant_id.compute_price()


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    @api.multi
    def compute_price(self):
        bom_obj = self.env['mrp.bom']
        action_rec = self.env.ref('stock_account.action_view_change_standard_price')
        for product in self:
            bom = bom_obj._bom_find(product=product)
            if bom:
                price = product._calc_price(bom)
                if action_rec:
                    action = action_rec.read([])[0]
                    action['context'] = {'default_new_price': price}
                    return action
        return True

    def _calc_price(self, bom):
        price = 0.0
        result, result2 = bom.explode(self, 1)
        for sbom, sbom_data in result2:
            if not sbom.attribute_value_ids:
                # No attribute_value_ids means the bom line is not variant specific
                price += sbom.product_id.uom_id._compute_price(sbom.product_id.standard_price, sbom.product_uom_id) * sbom_data['qty']
        if bom.routing_id:
            # FIXME master: remove me
            if hasattr(self.env['mrp.workcenter'], 'costs_hour'):                
                total_cost = 0.0
                for order in bom.routing_id.operation_ids:
                    total_cost += (order.time_cycle/60) * order.workcenter_id.costs_hour
                price += bom.product_uom_id._compute_price(total_cost, bom.product_id.uom_id)
        # Convert on product UoM quantities
        if price > 0:
            price = bom.product_uom_id._compute_price(price / bom.product_qty, self.uom_id)
        return price
