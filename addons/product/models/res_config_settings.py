# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_discount_per_so_line = fields.Boolean("Discounts", implied_group='product.group_discount_per_so_line')
    group_uom = fields.Boolean("Units of Measure", implied_group='uom.group_uom')
    group_product_variant = fields.Boolean("Variants", implied_group='product.group_product_variant')
    module_sale_product_matrix = fields.Boolean("Sales Grid Entry")
    module_loyalty = fields.Boolean("Promotions, Coupons, Gift Card & Loyalty Program")
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
    company_weight_uom_id = fields.Many2one('uom.uom', string='Weight unit of measure', related='company_id.default_weight_uom_id', readonly=False)
    company_volume_uom_id = fields.Many2one('uom.uom', string='Volume unit of measure', related='company_id.default_volume_uom_id', readonly=False)
    company_dimension_uom_id = fields.Many2one('uom.uom', string='Dimension unit of measure', related='company_id.default_dimension_uom_id', readonly=False)

    @api.onchange('group_product_variant')
    def _onchange_group_product_variant(self):
        """The product Configurator requires the product variants activated.
        If the user disables the product variants -> disable the product configurator as well"""
        if self.module_sale_product_matrix and not self.group_product_variant:
            self.module_sale_product_matrix = False

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
        super().set_values()
        if not self.group_discount_per_so_line:
            pl = self.env['product.pricelist'].search([('discount_policy', '=', 'without_discount')])
            pl.write({'discount_policy': 'with_discount'})
