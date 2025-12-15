# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    def _get_stock_moves_to_consider(self, stock_moves, product):
        self.ensure_one()
        bom = product.env['mrp.bom']._bom_find(product, company_id=stock_moves.company_id.id, bom_type='phantom').get(product)
        if not bom:
            return super()._get_stock_moves_to_consider(stock_moves, product)
        boms, components = bom.explode(product, self.qty)
        #Get a flat list of all bom_line_ids
        bom_line_ids = [item.id for x in boms for item in x[0].bom_line_ids if set(item.bom_product_template_attribute_value_ids.ids).issubset(product.product_template_variant_value_ids.ids)]
        ml_product_to_consider = (product.bom_ids and [comp[0].product_id.id for comp in components]) or [product.id]
        return stock_moves.filtered(lambda ml: ml.product_id.id in ml_product_to_consider and (ml.bom_line_id.id in bom_line_ids))


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _get_pos_anglo_saxon_price_unit(self, product, partner_id, quantity):
        bom = product.env['mrp.bom']._bom_find(product, company_id=self.mapped('picking_ids.move_line_ids').company_id.id, bom_type='phantom')[product]
        if not bom:
            return super()._get_pos_anglo_saxon_price_unit(product, partner_id, quantity)
        _dummy, components = bom.explode(product, quantity)
        total_price_unit = 0
        for comp in components:
            price_unit = super()._get_pos_anglo_saxon_price_unit(comp[0].product_id, partner_id, comp[1]['qty'])
            price_unit = comp[0].product_id.uom_id._compute_price(price_unit, comp[0].product_uom_id)
            qty_per_kit = comp[1]['qty'] / bom.product_qty / (quantity or 1)
            total_price_unit += price_unit * qty_per_kit
        return total_price_unit
