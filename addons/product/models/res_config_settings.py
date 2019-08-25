# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_discount_per_so_line = fields.Boolean("Discounts", implied_group='product.group_discount_per_so_line')
    group_uom = fields.Boolean("Units of Measure", implied_group='uom.group_uom')
    group_product_variant = fields.Boolean("Variants", implied_group='product.group_product_variant')
    module_sale_product_configurator = fields.Boolean("Product Configurator")
    module_sale_product_matrix = fields.Boolean("Sales Grid Entry")
    group_stock_packaging = fields.Boolean('Product Packagings',
        implied_group='product.group_stock_packaging')
    group_product_pricelist = fields.Boolean("Pricelists",
        implied_group='product.group_product_pricelist')
    group_sale_pricelist = fields.Boolean("Advanced Pricelists",
        implied_group='product.group_sale_pricelist',
        help="""Allows to manage different prices based on rules per category of customers.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc.""")
    product_pricelist_setting = fields.Selection([
            ('basic', 'Multiple prices per product'),
            ('advanced', 'Advanced price rules (discounts, formulas)')
            ], default='basic', string="Pricelists Method", config_parameter='product.product_pricelist_setting',
            help="Multiple prices: Pricelists with fixed price rules by product,\nAdvanced rules: enables advanced price rules for pricelists.")
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
        if self.module_sale_product_matrix and not self.group_product_variant:
            self.module_sale_product_matrix = False

    @api.onchange('module_sale_product_configurator')
    def _onchange_module_sale_product_configurator(self):
        """The product Configurator requires the product variants activated
        If the user enables the product configurator -> enable the product variants as well"""
        if self.module_sale_product_configurator and not self.group_product_variant:
            self.group_product_variant = True

    @api.onchange('group_multi_currency')
    def _onchange_group_multi_currency(self):
        if self.group_product_pricelist and not self.group_sale_pricelist and self.group_multi_currency:
            self.group_sale_pricelist = True

    @api.onchange('group_product_pricelist')
    def _onchange_group_sale_pricelist(self):
        if not self.group_product_pricelist and self.group_sale_pricelist:
            self.group_sale_pricelist = False

    @api.onchange('product_pricelist_setting')
    def _onchange_product_pricelist_setting(self):
        if self.product_pricelist_setting == 'basic':
            self.group_sale_pricelist = False
        else:
            self.group_sale_pricelist = True

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if not self.group_discount_per_so_line:
            pl = self.env['product.pricelist'].search([('discount_policy', '=', 'without_discount')])
            pl.write({'discount_policy': 'with_discount'})

    @api.onchange('module_sale_product_matrix')
    def _onchange_module_module_sale_product_matrix(self):
        """The product Grid Configurator requires the product Configurator activated
        If the user enables the Grid Configurator -> enable the product Configurator as well"""
        if self.module_sale_product_matrix and not self.module_sale_product_configurator:
            self.module_sale_product_configurator = True
