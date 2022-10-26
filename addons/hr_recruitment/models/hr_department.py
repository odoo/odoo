# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    new_applicant_count = fields.Integer(
        compute='_compute_new_applicant_count', string='New Applicant', compute_sudo=True)
    new_hired_employee = fields.Integer(
        compute='_compute_recruitment_stats', string='New Hired Employee')
    expected_employee = fields.Integer(
        compute='_compute_recruitment_stats', string='Expected Employee')

    def _compute_new_applicant_count(self):
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_interviewer'):
            applicant_data = self.env['hr.applicant']._read_group(
                [('department_id', 'in', self.ids), ('stage_id.sequence', '<=', '1')],
                ['department_id'], ['department_id'])
            result = dict((data['department_id'][0], data['department_id_count']) for data in applicant_data)
            for department in self:
                department.new_applicant_count = result.get(department.id, 0)
        else:
            self.new_applicant_count = 0

    def _compute_recruitment_stats(self):
        job_data = self.env['hr.job']._read_group(
            [('department_id', 'in', self.ids)],
            ['no_of_hired_employee', 'no_of_recruitment', 'department_id'], ['department_id'])
        new_emp = dict((data['department_id'][0], data['no_of_hired_employee']) for data in job_data)
        expected_emp = dict((data['department_id'][0], data['no_of_recruitment']) for data in job_data)
        for department in self:
            department.new_hired_employee = new_emp.get(department.id, 0)
            department.expected_employee = expected_emp.get(department.id, 0)
