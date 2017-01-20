# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    inventory_availability = fields.Selection([
        ('never', 'Don\'t show anything'),
        ('always', 'Show inventory'),
        ('threshold', 'Only show below a threshold'),
        ('custom', 'Custom message'),
    ], string='Inventory Availability', default=lambda self: self.env['ir.values'].get_default('website.config.settings', 'inventory_availability'), help='Adds an inventory availability status on the web product page.')
    available_threshold = fields.Float(string='Available Threshold', default=lambda self: 5 if self.env['ir.values'].get_default('website.config.settings', 'inventory_availability') == 'threshold' else None)
    custom_message = fields.Text(string='Custom Message')
