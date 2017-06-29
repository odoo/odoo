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
    ], string='Inventory Availability', help='Adds an inventory availability status on the web product page.', default='never')
    available_threshold = fields.Float(string='Available Threshold', default=5.0)
    custom_message = fields.Text(string='Custom Message', default='')
