# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_uom = fields.Boolean("Units of Measure", implied_group='uom.group_uom')
    group_product_variant = fields.Boolean("Variants", implied_group='product.group_product_variant')
    module_sale_product_configurator = fields.Boolean("Product Configurator")
    group_stock_packaging = fields.Boolean('Product Packagings',
        implied_group='product.group_stock_packaging')
    group_sale_pricelist = fields.Boolean("Use pricelists to adapt your price per customers",
        implied_group='product.group_sale_pricelist',
        help="""Allows to manage different prices based on rules per category of customers.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc.""")
    group_product_pricelist = fields.Boolean("Show pricelists On Products",
        implied_group='product.group_product_pricelist')
    group_pricelist_item = fields.Boolean("Show pricelists to customers",
         implied_group='product.group_pricelist_item')
    product_weight_in_lbs = fields.Selection([
        ('0', 'Kilogram'),
        ('1', 'Pound'),
    ], 'Weight unit of measure', config_parameter='product.weight_in_lbs', default='0')
    product_volume_volume_in_cubic_feet = fields.Selection([
        ('0', 'Cubic Meters'),
        ('1', 'Cubic Feet'),
    ], 'Volume unit of measure', config_parameter='product.volume_in_cubic_feet', default='0')

    @api.onchange('group_product_variant')
    def _onchange_group_product_variant(self):
        """The product Configurator requires the product variants activated.
        If the user disables the product variants -> disable the product configurator as well"""
        if self.module_sale_product_configurator and not self.group_product_variant:
            self.module_sale_product_configurator = False

    @api.onchange('module_sale_product_configurator')
    def _onchange_module_sale_product_configurator(self):
        """The product Configurator requires the product variants activated
        If the user enables the product configurator -> enable the product variants as well"""
        if self.module_sale_product_configurator and not self.group_product_variant:
            self.group_product_variant = True
