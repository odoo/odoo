# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    manufacturing_lead = fields.Float(related='company_id.manufacturing_lead', string="Manufacturing Lead Time")
    use_manufacturing_lead = fields.Boolean(string="Default Manufacturing Lead Time", oldname='default_use_manufacturing_lead')
    module_mrp_byproduct = fields.Boolean("By-Products")
    module_mrp_mps = fields.Boolean("Master Production Schedule")
    group_mrp_routings = fields.Boolean("Work Orders",
        implied_group='mrp.group_mrp_routings')

    @api.model
    def get_values(self):
        res = super(MrpConfigSettings, self).get_values()
        res.update(
            use_manufacturing_lead=self.env['ir.config_parameter'].sudo().get_param('mrp.use_manufacturing_lead')
        )
        return res

    @api.multi
    def set_values(self):
        super(MrpConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('mrp.use_manufacturing_lead', self.use_manufacturing_lead)

    @api.onchange('use_manufacturing_lead')
    def _onchange_use_manufacturing_lead(self):
        if not self.use_manufacturing_lead:
            self.manufacturing_lead = 0.0