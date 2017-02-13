# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProdcuctCatalogSettings(models.TransientModel):
    _name = "product.catalog.settings"
    _inherit = "res.config.settings"

    group_product_variant = fields.Selection([
        (0, "No variants on products"),
        (1, 'Products can have several attributes, defining variants (Example: size, color,...)')
    ], string="Product Variants",
        help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example',
        implied_group='product.group_product_variant')
    group_uom = fields.Selection([
        (0, 'Products have only one unit of measure (easier)'),
        (1, 'Some products may be sold/purchased in different unit of measures (advanced)')
    ], string="Unit of Measures", implied_group='product.group_uom',
        help="""Allows you to select and maintain different units of measure for products.""")
