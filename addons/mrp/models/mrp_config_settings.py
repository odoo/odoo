# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpConfigSettings(models.TransientModel):
    _name = 'mrp.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    manufacturing_lead = fields.Float(related='company_id.manufacturing_lead', string="Manufacturing Lead Time")
    use_manufacturing_lead = fields.Boolean(string="Default Manufacturing Lead Time", oldname='default_use_manufacturing_lead')
    group_product_variant = fields.Boolean("Attributes & Variants",
        implied_group='product.group_product_variant')
    module_mrp_byproduct = fields.Boolean("By-Products")
    module_mrp_mps = fields.Boolean("Master Production Schedule")
    module_mrp_plm = fields.Boolean("Product Lifecycle Management")
    module_mrp_maintenance = fields.Boolean("Maintenance")
    module_quality_mrp = fields.Boolean("Quality Control")
    group_mrp_routings = fields.Boolean("Work Orders",
        implied_group='mrp.group_mrp_routings')
    module_mrp_repair = fields.Boolean("Repair")

    @api.model
    def get_default_fields(self, fields):
        return dict(
            use_manufacturing_lead=self.env['ir.config_parameter'].sudo().get_param('mrp.use_manufacturing_lead')
        )

    @api.multi
    def set_fields(self):
        self.env['ir.config_parameter'].sudo().set_param('mrp.use_manufacturing_lead', self.use_manufacturing_lead)

    @api.onchange('use_manufacturing_lead')
    def _onchange_use_manufacturing_lead(self):
        if not self.use_manufacturing_lead:
            self.manufacturing_lead = 0.0