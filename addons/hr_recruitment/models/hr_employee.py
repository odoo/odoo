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

    @api.model
    def create(self, vals):
        new_employee = super(HrEmployee, self).create(vals)
        if new_employee.applicant_id:
            new_employee.applicant_id.message_post_with_view(
                        'hr_recruitment.applicant_hired_template',
                        values={'applicant': new_employee.applicant_id},
                        subtype_id=self.env.ref("hr_recruitment.mt_applicant_hired").id)
            if new_employee.company_id.refuse_existing_applications:
                other_applications = self.env['hr.applicant'].search([
                    ('partner_id', 'in', new_employee.applicant_id.partner_id.ids),
                    ('id', '!=', new_employee.applicant_id.id),
                ])
                other_applications.write({
                    'refuse_reason_id': self.env.ref('hr_recruitment.refuse_reason_4', raise_if_not_found=False).id,
                    'active': False,
                    'emp_id': new_employee.id,
                })
        return new_employee
