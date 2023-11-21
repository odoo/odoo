# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    def _get_stock_moves_to_consider(self, stock_moves, product):
        bom = product.env['mrp.bom']._bom_find(product, company_id=stock_moves.company_id.id, bom_type='phantom')[product]
        if not bom:
            return super()._get_stock_moves_to_consider(stock_moves, product)
        ml_product_to_consider = (product.bom_ids and bom.bom_line_ids.mapped('product_id').mapped('id')) or [product.id]
        return stock_moves.filtered(lambda ml: ml.product_id.id in ml_product_to_consider and ml.bom_line_id)

class PosOrder(models.Model):
    _inherit = "pos.order"

    def _get_pos_anglo_saxon_price_unit(self, product, partner_id, quantity):
        bom = product.env['mrp.bom']._bom_find(product, company_id=self.mapped('picking_ids.move_lines').company_id.id, bom_type='phantom')[product]
        if not bom:
            return super()._get_pos_anglo_saxon_price_unit(product, partner_id, quantity)
        dummy, components = bom.explode(product, quantity)
        return sum(super(PosOrder, self)._get_pos_anglo_saxon_price_unit(comp[1]['product'], partner_id, comp[1]['qty']) for comp in components)
