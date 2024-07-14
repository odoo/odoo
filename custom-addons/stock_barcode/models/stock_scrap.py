# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockScrap(models.Model):
    _name = 'stock.scrap'
    _inherit = ['stock.scrap', 'barcodes.barcode_events_mixin']

    product_barcode = fields.Char(related='product_id.barcode', string='Barcode', readonly=False)

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        product = self.env['product.product'].search([('barcode', '=', barcode)])
        if product and self.product_id == product:
            self.scrap_qty += 1
        elif product:
            self.scrap_qty = 1
            self.product_id = product
            self.lot_id = False
        else:
            lot = self.env['stock.lot'].search([('name', '=', barcode)])
            if lot and self.lot_id == lot:
                self.scrap_qty += 1
            elif lot:
                self.scrap_qty = 1
                self.lot_id = lot.id
                self.product_id = lot.product_id
