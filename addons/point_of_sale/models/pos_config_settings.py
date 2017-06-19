# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class PosConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'pos.config.settings'

    group_multi_currency = fields.Boolean("Multi-Currencies", implied_group='base.group_multi_currency')
    group_product_variant = fields.Boolean("Attributes & Variants", implied_group='product.group_product_variant')
    group_product_pricelist = fields.Boolean("Show pricelists On Products",
        implied_group='product.group_product_pricelist')
    group_pricelist_item = fields.Boolean("Show pricelists to customers",
         implied_group='product.group_pricelist_item')
    group_sale_pricelist = fields.Boolean("Use pricelists to adapt your price per customers",
         implied_group='product.group_sale_pricelist',
         help="""Allows to manage different prices based on rules per category of customers.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc.""")
    use_pos_sale_price = fields.Boolean("A single sale price per product", oldname='default_sale_price')
    pos_pricelist_setting = fields.Selection([
        ('percentage', 'Multiple prices per product (e.g. quantity, shop-specific)'),
        ('formula', 'Price computed from formulas (discounts, margins, rounding)')
        ], string="Multiple Prices per Products",
        oldname='default_pricelist_setting')
    module_pos_restaurant = fields.Boolean(string="Restaurant")
    module_pos_loyalty = fields.Boolean(string="Loyalty Program")
    module_pos_discount = fields.Boolean(string="Global Discounts")
    module_pos_mercury = fields.Boolean(string="Credit Cards")
    module_pos_reprint = fields.Boolean(string="Reprint Receipt")
    module_pos_data_drinks = fields.Boolean(string="Import common drinks data")

    @api.onchange('use_pos_sale_price')
    def _onchange_fix_sale_price(self):
        if not self.use_pos_sale_price:
            self.pos_pricelist_setting = False
        if self.use_pos_sale_price and not self.pos_pricelist_setting:
            self.pos_pricelist_setting = 'percentage'

    @api.onchange('pos_pricelist_setting')
    def _onchange_sale_price(self):
        if self.pos_pricelist_setting == 'percentage':
            self.update({
                'group_product_pricelist': True,
                'group_sale_pricelist': True,
                'group_pricelist_item': False,
            })
        elif self.pos_pricelist_setting == 'formula':
            self.update({
                'group_product_pricelist': False,
                'group_sale_pricelist': True,
                'group_pricelist_item': True,
            })
        else:
            self.update({
                'group_product_pricelist': False,
                'group_sale_pricelist': False,
                'group_pricelist_item': False,
            })

    def get_values(self):
        res = super(PosConfigSettings, self).get_values()
        res.update(
            use_pos_sale_price=self.env['ir.config_parameter'].sudo().get_param('pos.use_pos_sale_price'),
            pos_pricelist_setting=self.env['ir.config_parameter'].sudo().get_param('pos.pos_pricelist_setting'),
        )
        return res

    def set_values(self):
        super(PosConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('pos.use_pos_sale_price', self.use_pos_sale_price)
        self.env['ir.config_parameter'].sudo().set_param('pos.pos_pricelist_setting', self.pos_pricelist_setting)
