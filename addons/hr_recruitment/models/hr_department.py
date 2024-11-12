# -*- coding: utf-8 -*-

from odoo import fields, models


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
                ['department_id'], ['__count'])
            result = {department.id: count for department, count in applicant_data}
            for department in self:
                department.new_applicant_count = result.get(department.id, 0)
        else:
            self.new_applicant_count = 0

    def _compute_recruitment_stats(self):
        job_data = self.env['hr.job']._read_group(
            [('department_id', 'in', self.ids)],
            ['department_id'], ['no_of_hired_employee:sum', 'no_of_recruitment:sum'])
        new_emp = {department.id: nb_employee for department, nb_employee, __ in job_data}
        expected_emp = {department.id: nb_recruitment for department, __, nb_recruitment in job_data}
        for department in self:
            department.new_hired_employee = new_emp.get(department.id, 0)
            department.expected_employee = expected_emp.get(department.id, 0)
