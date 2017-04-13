# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    product_barcode = fields.Char(related='product_id.barcode')


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'barcodes.barcode_events_mixin']

    def on_barcode_scanned(self, barcode):
        product = self.env['product.product'].search([('barcode', '=', barcode), ('purchase_ok', '=', True)], limit=1)
        if product:
            corresponding_line = self.order_line.filtered(lambda r: r.product_barcode == barcode)
            if corresponding_line:
                corresponding_line[0].product_qty += 1
                corresponding_line[0]._onchange_quantity()
            else:
                corresponding_line = self.order_line.new({
                    'product_id': product.id,
                    'product_qty': 1.0,
                })
                self.order_line += corresponding_line
                corresponding_line.onchange_product_id()
