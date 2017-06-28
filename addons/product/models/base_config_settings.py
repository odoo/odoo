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
    weight_uom_id = fields.Many2one(
        'product.uom', 'Weight unit of measure', domain=lambda self: [('category_id', '=', self.env.ref('product.product_uom_categ_kgm').id)],
        help="This company will store weights in this unit of measure.")
    volume_uom_id = fields.Many2one(
        'product.uom', 'Volume unit of measure', domain=lambda self: [('category_id', '=', self.env.ref('product.product_uom_categ_vol').id)],
        help="This company will store volumes in this unit of measure.")

    @api.model
    def get_values(self):
        res = super(BaseConfigSettings, self).get_values()
        product_rule = self.env.ref('product.product_comp_rule')
        get_param = self.env['ir.config_parameter'].get_param
        res.update(
            company_share_product=not bool(product_rule.active),
            weight_uom_id=int(get_param('database_weight_uom_id')),
            volume_uom_id=int(get_param('database_volume_uom_id'))
        )
        return res

    def set_values(self):
        super(BaseConfigSettings, self).set_values()
        product_rule = self.env.ref('product.product_comp_rule')
        product_rule.write({'active': not bool(self.company_share_product)})
        set_param = self.env['ir.config_parameter'].set_param
        set_param('database_weight_uom_id', self.weight_uom_id.id)
        set_param('database_volume_uom_id', self.volume_uom_id.id)
