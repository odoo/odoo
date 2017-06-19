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

    @api.model
    def get_values(self):
        res = super(BaseConfigSettings, self).get_values()
        product_rule = self.env.ref('product.product_comp_rule')
        res.update(
            company_share_product=not bool(product_rule.active),
        )
        return res

    def set_values(self):
        super(BaseConfigSettings, self).set_values()
        product_rule = self.env.ref('product.product_comp_rule')
        product_rule.write({'active': not bool(self.company_share_product)})
