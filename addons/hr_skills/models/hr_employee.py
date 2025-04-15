# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import convert, SQL


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
        return super().create(vals_list)

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

    @api.model
    def get_internal_resume_lines(self, res_id, res_model):
        if not res_id:
            return []
        if res_model == 'res.users':
            res_id = self.env['res.users'].browse(res_id).employee_id.id
        self.env.cr.execute(SQL(
            '''
                WITH relevant_records AS (
                    SELECT date_version AS date_start, job_title,
                           job_title IS DISTINCT FROM (LAG(job_title) OVER (ORDER BY date_version)) AS is_changed
                      FROM hr_version
                     WHERE employee_id=%s
                )
                SELECT job_title, date_start,
                       (LEAD(date_start) OVER (ORDER BY date_start) - INTERVAL '1 day')::DATE date_end
                  FROM relevant_records
                 WHERE is_changed
                 ORDER BY date_start DESC
            ''', res_id)
        )
        query_result = self.env.cr.fetchall()
        res = []
        for rec in query_result:
            res.append({
                'job_title': rec[0],
                'date_start': rec[1],
                'date_end': rec[2]
            })
        return res
