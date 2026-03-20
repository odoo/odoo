# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    resume_line_ids = fields.One2many('hr.resume.line', 'employee_id', string="Resume lines")
    employee_skill_ids = fields.One2many('hr.employee.skill', 'employee_id', string="Skills",
        domain=[('skill_type_id.active', '=', True)])
    current_employee_skill_ids = fields.One2many('hr.employee.skill', related='employee_id.current_employee_skill_ids')
    skill_proficiency_ids = fields.Many2many('hr.skill.proficiency', related='employee_id.skill_proficiency_ids')
    certification_ids = fields.One2many('hr.employee.skill', related='employee_id.certification_ids')
    display_certification_page = fields.Boolean(related="employee_id.display_certification_page")

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if res.get('employee_skill_ids'):
            res['employee_skill_ids']['searchable'] = False
        return res
