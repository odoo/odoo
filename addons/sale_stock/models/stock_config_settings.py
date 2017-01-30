# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    security_lead = fields.Float(related='company_id.security_lead')
    default_new_security_lead = fields.Boolean(string="Security Lead Time for Sales", default_model="stock.config.settings", help="Margin of error for dates promised to customers. Products will be scheduled for procurement and delivery that many days earlier than the actual promised date, to cope with unexpected delays in the supply chain.")
    default_picking_policy = fields.Selection([
        ('direct', 'Ship products as soon as available, with back orders'),
        ('one', 'Ship all products at once')
        ], "Shipping Management", default='direct', default_model="sale.order", required=True)
