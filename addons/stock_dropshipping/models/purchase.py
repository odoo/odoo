# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sale_line_ids = fields.Many2many(
        'sale.order.line', 'purchase_sale_line_rel', 'purchase_line_id', 'sale_line_id')

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        res = super()._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)
        res['sale_line_ids'] = line.sale_line_ids.ids + values.get('sale_line_ids', [])
        return res

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, company_id, values, po):
        res = super()._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, company_id, values, po)
        res['sale_line_ids'] = values.get('sale_line_ids', False)
        return res
