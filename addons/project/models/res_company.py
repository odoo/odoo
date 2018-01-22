# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    project_time_mode_id = fields.Many2one('product.uom', string='Project Time Unit',
        default=lambda s: s.env.ref('product.product_uom_hour', raise_if_not_found=False),
        help="This will set the unit of measure used in projects and tasks.\n"
             "If you use the timesheet linked to projects, don't "
             "forget to setup the right unit of measure in your employees.")
