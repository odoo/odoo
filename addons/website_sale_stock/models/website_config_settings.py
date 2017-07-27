# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    inventory_availability = fields.Selection([
        ('never', 'Sell regardless of inventory'),
        ('always', 'Show inventory on website and prevent sales if not enough stock'),
        ('threshold', 'Show inventory below a threshold and prevent sales if not enough stock'),
        ('custom', 'Show product-specific notifications'),
    ], string='Inventory', default='never')
    available_threshold = fields.Float(string='Availability Threshold')

    @api.multi
    def set_values(self):
        super(WebsiteConfigSettings, self).set_values()
        self.env['ir.values'].sudo().set_default('product.template', 'inventory_availability', self.inventory_availability)
        self.env['ir.values'].sudo().set_default('product.template', 'available_threshold', self.available_threshold if self.inventory_availability == 'threshold' else None)

    @api.model
    def get_values(self):
        res = super(WebsiteConfigSettings, self).get_values()
        param = self.env['ir.values'].sudo()
        res.update(inventory_availability=param.get_default('product.template', 'inventory_availability') or 'never',
                   available_threshold=param.get_default('product.template', 'available_threshold') or 5.0
                   )
        return res
