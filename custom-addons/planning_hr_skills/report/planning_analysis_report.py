# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class PlanningAnalysisReport(models.Model):
    _inherit = "planning.analysis.report"

    # Not using a related as we want to avoid having a depends.
    employee_skill_ids = fields.One2many('hr.employee.skill', string='Skills', compute='_compute_employee_skill_ids',
                                         search='_search_employee_skill_ids')

    def _compute_employee_skill_ids(self):
        for slot in self:
            slot.employee_skill_ids = slot.employee_id.employee_skill_ids

    @api.model
    def _search_employee_skill_ids(self, operator, value):
        return [('employee_id.employee_skill_ids', operator, value)]
