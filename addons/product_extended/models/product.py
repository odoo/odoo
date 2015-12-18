# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def compute_standard_price(self, variants=False, recursive=False, real_time_accounting=False):
        MrpBom = self.env['mrp.bom']
        records = variants or self
        pricedict = {}
        for product in records:
            if variants:
                bom_id = MrpBom._bom_find(product_id=product.id)
            else:
                bom_id = MrpBom._bom_find(product_tmpl_id=product.id)
            if bom_id:
                bom = MrpBom.browse(bom_id)
                if recursive:
                    self.compute_standard_price(bom.bom_line_ids.mapped('product_id'), recursive=recursive, real_time_accounting=real_time_accounting)
                price = self._compute_standard_price(bom, real_time_accounting=real_time_accounting)
                pricedict[product.id] = price
                if not self.env.context.get('no_update'):
                    if (product.valuation != "real_time" or not real_time_accounting):
                        product.standard_price = price
                    else:
                        product.do_change_standard_price(price)
        return pricedict

    def _compute_standard_price(self, bom, real_time_accounting=False):
        price = 0
        ProductUom = self.env['product.uom']
        # No attribute_value_ids means the bom line is not variant specific
        for bom_line in bom.bom_line_ids.filtered(lambda line: not line.attribute_value_ids):
            my_qty = bom_line.product_qty / bom_line.product_efficiency
            price += ProductUom._compute_price(bom_line.product_id.uom_id.id, bom_line.product_id.standard_price, bom_line.product_uom.id) * my_qty
        for wline in bom.routing_id.workcenter_lines:
            wc = wline.workcenter_id
            cycle = wline.cycle_nbr
            hour = (wc.time_start + wc.time_stop + cycle * wc.time_cycle) *  (wc.time_efficiency or 1.0)
            price += wc.costs_cycle * cycle + wc.costs_hour * hour
            price = ProductUom._compute_price(bom.product_uom.id, price, bom.product_id.uom_id.id)
        #Convert on product UoM quantities
        if price > 0:
            price = ProductUom._compute_price(bom.product_uom.id, price / bom.product_qty, bom.product_id.uom_id.id)
        return price
