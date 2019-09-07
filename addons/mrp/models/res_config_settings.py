# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    manufacturing_lead = fields.Float(related='company_id.manufacturing_lead', string="Manufacturing Lead Time", readonly=False)
    use_manufacturing_lead = fields.Boolean(string="Default Manufacturing Lead Time", config_parameter='mrp.use_manufacturing_lead')
    group_mrp_byproducts = fields.Boolean("By-Products",
        implied_group='mrp.group_mrp_byproducts')
    module_mrp_mps = fields.Boolean("Master Production Schedule")
    module_mrp_plm = fields.Boolean("Product Lifecycle Management (PLM)")
    module_mrp_workorder = fields.Boolean("Work Orders")
    module_quality_control = fields.Boolean("Quality")
    module_mrp_subcontracting = fields.Boolean("Subcontracting")
    group_mrp_routings = fields.Boolean("MRP Work Orders",
        implied_group='mrp.group_mrp_routings')

    @api.onchange('use_manufacturing_lead')
    def _onchange_use_manufacturing_lead(self):
        if not self.use_manufacturing_lead:
            self.manufacturing_lead = 0.0

    @api.onchange('group_mrp_routings')
    def _onchange_group_mrp_routings(self):
        # If we activate 'MRP Work Orders', it means that we need to install 'mrp_workorder'.
        # The opposite is not always true: other modules (such as 'quality_mrp_workorder') may
        # depend on 'mrp_workorder', so we should not automatically uninstall the module if 'MRP
        # Work Orders' is deactivated.
        # Long story short: if 'mrp_workorder' is already installed, we don't uninstall it based on
        # group_mrp_routings
        if self.group_mrp_routings:
            self.module_mrp_workorder = True
        elif not self.env['ir.module.module'].search([('name', '=', 'mrp_workorder'), ('state', '=', 'installed')]):
            self.module_mrp_workorder = False
