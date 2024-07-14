# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'
    _barcode_field = 'barcode'

    def _get_stock_barcode_specific_data(self):
        products = self.product_id
        return {
            'product.product': products.read(self.env['product.product']._get_fields_stock_barcode(), load=False),
            'uom.uom': products.uom_id.read(self.env['uom.uom']._get_fields_stock_barcode(), load=False)
        }

    @api.model
    def _get_fields_stock_barcode(self):
        return ['barcode', 'product_id', 'qty', 'name']
