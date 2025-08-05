# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import convert

# DONE
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    resume_line_ids = fields.One2many('hr.resume.line', 'employee_id', string="Resume lines")
    employee_skill_ids = fields.One2many('hr.employee.skill', 'employee_id', string="Skills",
        domain=[('skill_type_id.active', '=', True)])
    current_employee_skill_ids = fields.One2many('hr.employee.skill',
        compute='_compute_current_employee_skill_ids', readonly=False)
    skill_ids = fields.Many2many('hr.skill', compute='_compute_skill_ids', store=True, groups="hr.group_hr_user")
    certification_ids = fields.One2many('hr.employee.skill', compute='_compute_certification_ids', readonly=False)

    @api.depends('employee_skill_ids')
    def _compute_current_employee_skill_ids(self):
        current_employee_skill_by_employee = self.employee_skill_ids.get_current_skills_by_employee()
        for employee in self:
            employee.current_employee_skill_ids = current_employee_skill_by_employee[employee.id]

    @api.depends('employee_skill_ids.skill_id')
    def _compute_skill_ids(self):
        for employee in self:
            employee.skill_ids = employee.employee_skill_ids.skill_id

    @api.depends('employee_skill_ids')
    def _compute_certification_ids(self):
        for employee in self:
            employee.certification_ids = employee.employee_skill_ids.filtered('is_certification')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals_emp_skill = vals.pop('current_employee_skill_ids', [])\
                + vals.pop('certification_ids', []) + vals.get('employee_skill_ids', [])
            vals['employee_skill_ids'] = self.env['hr.employee.skill']._get_transformed_commands(vals_emp_skill, self)
        res = super().create(vals_list)
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
        if 'current_employee_skill_ids' in vals or 'certification_ids' in vals or 'employee_skill_ids' in vals:
            vals_emp_skill = vals.pop('current_employee_skill_ids', []) + vals.pop('certification_ids', [])\
                + vals.get('employee_skill_ids', [])
            vals['employee_skill_ids'] = self.env['hr.employee.skill']._get_transformed_commands(vals_emp_skill, self)
        return super().write(vals)

    def _load_scenario(self):
        super()._load_scenario()
        demo_tag = self.env.ref('hr_skills.employee_resume_line_emp_eg_1', raise_if_not_found=False)
        if demo_tag:
            return
        convert.convert_file(self.env, 'hr', 'data/scenarios/hr_scenario.xml', None, mode='init')
        convert.convert_file(self.env, 'hr_skills', 'data/scenarios/hr_skills_scenario.xml', None, mode='init')
