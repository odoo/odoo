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
            result = self.env['hr.applicant']._aggregate(
                [('department_id', 'in', self.ids), ('stage_id.sequence', '<=', '1')],
                ['*:count'], ['department_id'])
            for department in self:
                department.new_applicant_count = result.get_agg(department.id, '*:count', 0)
        else:
            self.new_applicant_count = 0

    def _compute_recruitment_stats(self):
        job_data = self.env['hr.job']._aggregate(
            [('department_id', 'in', self.ids)],
            ['no_of_hired_employee:sum', 'no_of_recruitment:sum'], ['department_id'])
        for department in self:
            department.new_hired_employee = job_data.get_agg(department.id, 'no_of_hired_employee:sum', 0)
            department.expected_employee = job_data.get_agg(department.id, 'no_of_recruitment:sum', 0)
