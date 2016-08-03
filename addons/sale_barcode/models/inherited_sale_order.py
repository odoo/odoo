# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'barcodes.barcode_events_mixin']

    def on_barcode_scanned(self, barcode):
        product = self.env['product.product'].search([('barcode', '=', barcode), ('sale_ok', '=', True)], limit=1)
        if product:
            order_line = self.order_line.filtered(lambda line: line.product_id == product)
            if order_line:
                order_line[0].product_uom_qty += 1
                order_line[0].product_uom_change()
            else:
                order_line = self.order_line.new({
                    'product_id': product.id,
                    'product_uom_qty': 1.0,
                })
                self.order_line += order_line
                order_line.product_id_change()
