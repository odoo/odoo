# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpConfigSettings(models.TransientModel):
    _name = 'mrp.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    manufacturing_lead = fields.Float(related='company_id.manufacturing_lead', string="Manufacturing Lead Time *")
    group_product_variant = fields.Selection([
        (0, "No variants on products"),
        (1, 'Products can have several attributes, defining variants (Example: size, color,...)')], "Product Variants",
        help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example',
        implied_group='product.group_product_variant')
    module_mrp_byproduct = fields.Selection([
        (0, "No by-products in bills of materials (A + B --> C)"),
        (1, "Bills of materials may produce residual products (A + B --> C + D)")], "By-Products",
        help='You can configure by-products in the bill of material.\n'
             'Without this module: A + B + C -> D.\n'
             'With this module: A + B + C -> D + E.\n'
             '-This installs the module mrp_byproduct.')
    module_mrp_mps = fields.Selection([
        (0, "No need for Master Production Schedule as products have short lead times"), 
        (1, "Use Master Production Schedule in order to create procurements based on forecasts"),
        ], string="Master Production Schedule")
    module_mrp_plm = fields.Selection([
        (0, "No product lifecycle management"),
        (1, "Manage engineering changes, versions and documents")
        ], string="PLM")
    module_mrp_maintenance = fields.Selection([
        (0, "No maintenance machine and work centers"),
        (1, "Preventive and Corrective maintenance management")
        ], string="Maintenance")
    module_quality_mrp = fields.Selection([
        (0, "No quality control"),
        (1, "Manage quality control points, checks and measures")
        ], string="Quality")
    group_mrp_routings = fields.Selection([
        (0, "Manage production by manufacturing orders"),
        (1, "Manage production by work orders")], "Routings & Planning",
        implied_group='mrp.group_mrp_routings',
        help='Work Order Operations allow you to create and manage the manufacturing operations that should be followed '
             'within your work centers in order to produce a product. They are attached to bills of materials '
             'that will define the required raw materials.')
