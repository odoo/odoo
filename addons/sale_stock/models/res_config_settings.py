# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    security_lead = fields.Float(related='company_id.security_lead', string="Security Lead Time", readonly=False)
    use_security_lead = fields.Boolean(
        string="Security Lead Time for Sales",
        config_parameter='sale_stock.use_security_lead',
        help="Margin of error for dates promised to customers. Products will be scheduled for delivery that many days earlier than the actual promised date, to cope with unexpected delays in the supply chain.")
    picking_policy = fields.Selection([
        ('direct', 'As soon as available, with back orders'),
        ('one', 'When all products are ready')
        ], default='direct', config_parameter="sale_stock.picking_policy", required=True)

    @api.onchange('use_security_lead')
    def _onchange_use_security_lead(self):
        if not self.use_security_lead:
            self.security_lead = 0.0

    def set_values(self):
        old_picking_policy = self.env['ir.config_parameter'].sudo().get_param('sale_stock.picking_policy', 'direct')
        if self.picking_policy != old_picking_policy:
            picking_types = self.env['stock.picking.type'].search([
                ('code', '!=', 'incoming'),
                ('move_type', '!=', self.picking_policy)
            ])
            if picking_types:
                picking_types.move_type = self.picking_policy
        super().set_values()
