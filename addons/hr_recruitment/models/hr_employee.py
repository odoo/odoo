# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    applicant_ids = fields.One2many('hr.applicant', 'employee_id', 'Applicants', groups="hr.group_hr_user")

    def _get_partner_count_depends(self):
        return super()._get_partner_count_depends() + ['applicant_ids']

    def _get_related_partners(self):
        partners = super()._get_related_partners()
        return partners | self.sudo().applicant_ids.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for employee_sudo in employees.sudo():
            if employee_sudo.applicant_ids:
                # TODO: remove this comment:
                # Replaced the link with a regular text message, as:
                # 1. the link can't be dynamic (can't open a view based on user access rights (employee vs employee public))
                # 2. the smart button on the applicant does the job of the link.
                employee_sudo.applicant_ids.message_post(
                    body="Employee created.",
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )
        return employees
