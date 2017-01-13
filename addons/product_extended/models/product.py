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
        workcenter_cost = 0.0
        for sbom in bom.bom_line_ids:
            my_qty = sbom.product_qty
            if not sbom.attribute_value_ids:
                # No attribute_value_ids means the bom line is not variant specific
                price += sbom.product_id.uom_id._compute_price(sbom.product_id.standard_price, sbom.product_uom_id) * my_qty
        if bom.routing_id:
            total_cost = 0.0
            for order in bom.routing_id.operation_ids:
                total_cost += (order.time_cycle_manual/60) * order.workcenter_id.costs_hour
            workcenter_cost = total_cost / len(bom.routing_id.operation_ids)
            price += bom.product_uom_id._compute_price(workcenter_cost, bom.product_id.uom_id)
        # Convert on product UoM quantities
        if price > 0:
            price = bom.product_uom_id._compute_price(price / bom.product_qty, self.uom_id)
        return price
