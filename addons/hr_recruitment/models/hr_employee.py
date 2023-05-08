# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import _
from datetime import timedelta


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    newly_hired_employee = fields.Boolean('Newly hired employee', compute='_compute_newly_hired_employee',
                                          search='_search_newly_hired_employee')
    applicant_id = fields.One2many('hr.applicant', 'emp_id', 'Applicant')

    def _compute_newly_hired_employee(self):
        now = fields.Datetime.now()
        for employee in self:
            employee.newly_hired_employee = bool(employee.create_date > (now - timedelta(days=90)))

    def _search_newly_hired_employee(self, operator, value):
        employees = self.env['hr.employee'].search([
            ('create_date', '>', fields.Datetime.now() - timedelta(days=90))
        ])
        return [('id', 'in', employees.ids)]

    def default_get(self, fields):
        res = super().default_get(fields)
        # Add the work_contact_id to prevent the creation of a second contact with
        # `_inverse_work_contact_details` method of `hr.employee.base`
        if 'work_contact_id' in fields:
            current_applicant = self.env['hr.applicant'].browse(self.env.context.get('default_applicant_id'))
            if current_applicant:
                res['work_contact_id'] = current_applicant.partner_id.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for employee in employees:
            if employee.applicant_id:
                employee.applicant_id.message_post_with_view(
                    'hr_recruitment.applicant_hired_template',
                    values={'applicant': employee.applicant_id},
                    subtype_id=self.env.ref("hr_recruitment.mt_applicant_hired").id)
        return employees
