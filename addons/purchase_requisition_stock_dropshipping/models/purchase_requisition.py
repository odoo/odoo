# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def _prepare_tender_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        res = super()._prepare_tender_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        if 'sale_line_id' in values:
            res['line_ids'][0][2]['sale_line_id'] = values['sale_line_id']
        return res


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    sale_line_id = fields.Many2one('sale.order.line', string="Origin Sale Order Line")

    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        res = super()._prepare_purchase_order_line(name, product_qty, price_unit, taxes_ids)
        if self.sale_line_id:
            res['sale_line_id'] = self.sale_line_id.id
        return res
