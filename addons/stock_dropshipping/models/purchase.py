# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.multi
    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        for re in res:
            re['sale_line_id'] = self.sale_line_id.id
        return res

    def _merge_in_existing_line(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        if values.get('sale_line_id') and values['sale_line_id'] != self.sale_line_id.id:
            # if this is defined, this is a dropshipping line, so no
            # this is to correctly map delivered quantities to the so lines
            return False
        return super(PurchaseOrderLine, self)._merge_in_existing_line(
            product_id=product_id, product_qty=product_qty, product_uom=product_uom,
            location_id=location_id, name=name, origin=origin, values=values)

class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, supplier):
        res = super(StockRule, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, supplier)
        res['sale_line_id'] = values.get('sale_line_id', False)
        return res
