# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'

    security_lead = fields.Float(related='company_id.security_lead', string="Security Lead Time")
    group_route_so_lines = fields.Boolean("Order-Specific Routes",
        implied_group='sale_stock.group_route_so_lines')
    module_sale_order_dates = fields.Boolean("Delivery Date")
    group_display_incoterm = fields.Boolean("Incoterms", implied_group='sale_stock.group_display_incoterm')
