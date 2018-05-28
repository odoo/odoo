# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    manufacturing_lead = fields.Float(related='company_id.manufacturing_lead', string="Manufacturing Lead Time")
    use_manufacturing_lead = fields.Boolean(string="Default Manufacturing Lead Time", config_parameter='mrp.use_manufacturing_lead', oldname='default_use_manufacturing_lead')
    module_mrp_byproduct = fields.Boolean("By-Products")
    module_mrp_mps = fields.Boolean("Master Production Schedule")
    module_mrp_plm = fields.Boolean("Product Lifecycle Management (PLM)")
    module_mrp_maintenance = fields.Boolean("Maintenance")
    module_mrp_workorder = fields.Boolean("Work Orders")
    module_repair = fields.Boolean("Repair")
    module_quality_control = fields.Boolean("Quality")
    group_mrp_routings = fields.Boolean("MRP Work Orders",
        implied_group='mrp.group_mrp_routings')

    @api.onchange('use_manufacturing_lead')
    def _onchange_use_manufacturing_lead(self):
        if not self.use_manufacturing_lead:
            self.manufacturing_lead = 0.0

    @api.onchange('group_mrp_routings')
    def _onchange_group_mrp_routings(self):
        self.module_mrp_workorder = self.group_mrp_routings
