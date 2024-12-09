# Copyright 2021 VentorTech OU
# Part of Ventor modules. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductBarcodeMulti(models.Model):
    _name = 'product.barcode.multi'
    _description = 'Product Barcode Multi'

    name = fields.Char(
        'Barcode',
        required=True,
    )

    product_id = fields.Many2one(
        'product.product', 
        string='Product', 
        required=True,
        ondelete="cascade",
    )
