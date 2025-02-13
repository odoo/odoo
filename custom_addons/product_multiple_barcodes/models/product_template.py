# Copyright 2021 VentorTech OU
# Part of Ventor modules. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    barcode_ids = fields.One2many(related='product_variant_ids.barcode_ids', readonly=False)
