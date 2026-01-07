# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


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
            price_unit = comp[0].product_id.uom_id._compute_price(price_unit, comp[0].uom_id)
            qty_per_kit = comp[1]['qty'] / bom.product_qty / (quantity or 1)
            total_price_unit += price_unit * qty_per_kit
        return total_price_unit
