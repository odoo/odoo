# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpConfigSettings(models.TransientModel):
    _name = 'mrp.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    manufacturing_lead = fields.Float(related='company_id.manufacturing_lead', string="Manufacturing Lead Time")
    default_use_manufacturing_lead = fields.Boolean(string="Default Manufacturing Lead Time", default_model='mrp.config.settings')
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
