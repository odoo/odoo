# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Project(models.Model):
    _inherit = 'project.project'

    bom_line_id = fields.Many2one('mrp.bom.line')

    @api.constrains('sale_line_id', 'billable_type')
    def _check_sale_line_type(self):
        for project in self:
            if not project.sale_line_id or not project.sale_line_id.is_kit:
                super()._check_sale_line_type()
