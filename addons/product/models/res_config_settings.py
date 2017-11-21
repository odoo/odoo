# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_share_product = fields.Boolean(
        'Share product to all companies',
        help="Share your product to all companies defined in your instance.\n"
             " * Checked : Product are visible for every company, even if a company is defined on the partner.\n"
             " * Unchecked : Each company can see only its product (product where company is defined). Product not related to a company are visible for all companies.")
    group_uom = fields.Boolean("Units of Measure", implied_group='product.group_uom')
    group_product_variant = fields.Boolean("Attributes and Variants", implied_group='product.group_product_variant')
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


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        product_rule = self.env.ref('product.product_comp_rule')
        res.update(
            company_share_product=not bool(product_rule.active),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        product_rule = self.env.ref('product.product_comp_rule')
        product_rule.write({'active': not bool(self.company_share_product)})
