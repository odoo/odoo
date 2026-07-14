# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import convert


class Employee(models.Model):
    _inherit = 'hr.employee'

    resume_line_ids = fields.One2many('hr.resume.line', 'employee_id', string="Resume lines")
    employee_skill_ids = fields.One2many('hr.employee.skill', 'employee_id', string="Skills",
        domain=[('skill_type_id.active', '=', True)])
    skill_ids = fields.Many2many('hr.skill', compute='_compute_skill_ids', store=True, groups="hr.group_hr_user")

    @api.depends('employee_skill_ids.skill_id')
    def _compute_skill_ids(self):
        for employee in self:
            employee.skill_ids = employee.employee_skill_ids.skill_id

    @api.model_create_multi
    def create(self, vals_list):
        res = super(Employee, self).create(vals_list)
        if self.env.context.get('salary_simulation'):
            return res
        resume_lines_values = []
        for employee in res:
            line_type = self.env.ref('hr_skills.resume_type_experience', raise_if_not_found=False)
            resume_lines_values.append({
                'employee_id': employee.id,
                'name': employee.company_id.name or '',
                'date_start': employee.create_date.date(),
                'description': employee.job_title or '',
                'line_type_id': line_type and line_type.id,
            })
        self.env['hr.resume.line'].create(resume_lines_values)
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'department_id' in vals:
            self.employee_skill_ids._create_logs()
        return res

    def _load_scenario(self):
        super()._load_scenario()
        demo_tag = self.env.ref('hr_skills.employee_resume_line_emp_eg_1', raise_if_not_found=False)
        if demo_tag:
            return
        convert.convert_file(self.env, 'hr', 'data/scenarios/hr_scenario.xml', None, mode='init', kind='data')
        convert.convert_file(self.env, 'hr_skills', 'data/scenarios/hr_skills_scenario.xml', None, mode='init', kind='data')
