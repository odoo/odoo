# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    security_lead = fields.Float(related='company_id.security_lead', string="Security Lead Time", readonly=False)
    group_route_so_lines = fields.Boolean("Order-Specific Routes",
        implied_group='sale_stock.group_route_so_lines')
    group_display_incoterm = fields.Boolean("Incoterms", implied_group='sale_stock.group_display_incoterm')
    use_security_lead = fields.Boolean(
        string="Security Lead Time for Sales",
        config_parameter='sale_stock.use_security_lead',
        oldname='default_new_security_lead',
        help="Margin of error for dates promised to customers. Products will be scheduled for delivery that many days earlier than the actual promised date, to cope with unexpected delays in the supply chain.")
    default_picking_policy = fields.Selection([
        ('direct', 'Ship products as soon as available, with back orders'),
        ('one', 'Ship all products at once')
        ], "Picking Policy", default='direct', default_model="sale.order", required=True)

    @api.onchange('use_security_lead')
    def _onchange_use_security_lead(self):
        if not self.use_security_lead:
            self.security_lead = 0.0
