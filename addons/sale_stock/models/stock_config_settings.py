# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    security_lead = fields.Float(related='company_id.security_lead')
    use_security_lead = fields.Boolean(
        string="Security Lead Time for Sales",
        oldname='default_new_security_lead',
        help="Margin of error for dates promised to customers. Products will be scheduled for procurement and delivery that many days earlier than the actual promised date, to cope with unexpected delays in the supply chain.")
    default_picking_policy = fields.Selection([
        ('direct', 'Ship products as soon as available, with back orders'),
        ('one', 'Ship all products at once')
        ], "Shipping Management", default='direct', default_model="sale.order", required=True)

    @api.onchange('use_security_lead')
    def _onchange_use_security_lead(self):
        if not self.use_security_lead:
            self.security_lead = 0.0

    def get_default_fields(self, fields):
        return dict(
            use_security_lead=self.env['ir.config_parameter'].sudo().get_param('sale_stock.use_security_lead')
        )

    def set_fields(self):
        self.env['ir.config_parameter'].sudo().set_param('sale_stock.use_security_lead', self.use_security_lead)
