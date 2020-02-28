
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    bom_line_id = fields.Many2one('mrp.bom.line')

    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for task in self.sudo():
            if not task.sale_line_id.is_kit:
                super()._check_sale_line_type()
