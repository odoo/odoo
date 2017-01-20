# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    inventory_availability = fields.Selection([
        ('never', 'Don\'t show anything'),
        ('always', 'Show inventory'),
        ('threshold', 'Only show below a threshold'),
        ('custom', 'Custom message'),
    ], string='Default Inventory Visibility', default='never')

    def set_inventory_availability(self):
        return self.env['ir.values'].sudo().set_default('website.config.settings', 'inventory_availability', self.inventory_availability)
