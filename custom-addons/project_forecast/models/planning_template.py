# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class PlanningTemplate(models.Model):
    _inherit = 'planning.slot.template'

    project_id = fields.Many2one('project.project', string="Project",
                                 company_dependent=True, copy=True)

    @api.depends('project_id')
    def _compute_display_name(self):
        super()._compute_display_name()
        for shift_template in self:
            if shift_template.project_id:
                name = f'{shift_template.display_name} [{shift_template.project_id.display_name[:30]}]'
            else:
                name = shift_template.display_name
            shift_template.display_name = name
