# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    product_barcode = fields.Char(related='product_id.barcode')


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'barcodes.barcode_events_mixin']

    def on_barcode_scanned(self, barcode):
        product = self.env['product.product'].search([('barcode', '=', barcode), ('sale_ok', '=', True)], limit=1)
        if product:
            corresponding_line = self.order_line.filtered(lambda r: r.product_barcode == barcode)
            if corresponding_line:
                corresponding_line[0].product_uom_qty += 1
                corresponding_line[0].product_uom_change()
            else:
                corresponding_line = self.order_line.new({
                    'product_id': product.id,
                    'product_uom_qty': 1.0,
                })
                self.order_line += corresponding_line
                corresponding_line.product_id_change()
