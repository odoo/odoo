# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    company_share_product = fields.Boolean(
        'Share product to all companies',
        help="Share your product to all companies defined in your instance.\n"
             " * Checked : Product are visible for every company, even if a company is defined on the partner.\n"
             " * Unchecked : Each company can see only its product (product where company is defined). Product not related to a company are visible for all companies.")
    group_product_variant = fields.Selection([
        (0, "No variants on products"),
        (1, 'Products can have several attributes, defining variants (Example: size, color,...)')], "Product Variants",
        implied_group='product.group_product_variant',
        help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example')

    @api.model
    def get_default_company_share_product(self, fields):
        product_rule = self.env.ref('product.product_comp_rule')
        return {
            'company_share_product': not bool(product_rule.active)
        }

    @api.multi
    def set_auth_company_share_product(self):
        self.ensure_one()
        product_rule = self.env.ref('product.product_comp_rule')
        product_rule.write({'active': not bool(self.company_share_product)})
