# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    newly_hired_employee = fields.Boolean('Newly hired employee', compute='_compute_newly_hired_employee',
                                          search='_search_newly_hired_employee')

    def _compute_newly_hired_employee(self):
        read_group_result = self.env['hr.applicant'].read_group(
            [('emp_id', 'in', self.ids), ('job_id.state', '=', 'recruit')],
            ['emp_id'], ['emp_id'])
        result = dict((data['emp_id'], data['emp_id_count'] > 0) for data in read_group_result)
        for record in self:
            record.newly_hired_employee = result.get(record.id, False)

    def _search_newly_hired_employee(self, operator, value):
        applicants = self.env['hr.applicant'].search([('job_id.state', '=', 'recruit')])
        return [('id', 'in', applicants.ids)]
