# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, supplier):
        res = super(StockRule, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, supplier)
        res['sale_line_id'] = values.get('sale_line_id', False)
        return res
