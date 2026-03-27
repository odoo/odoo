# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # YTI Rename into candidate_ids
    candidate_id = fields.One2many('hr.candidate', 'employee_id', 'Candidate', groups="hr.group_hr_user")

    def _get_partner_count_depends(self):
        return super()._get_partner_count_depends() + ['candidate_id']

    def _get_related_partners(self):
        partners = super()._get_related_partners()
        return partners | self.sudo().candidate_id.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for employee in employees:
            if employee.candidate_id:
                employee.candidate_id._message_log_with_view(
                    'hr_recruitment.candidate_hired_template',
                    render_values={'candidate': employee.candidate_id}
                )
        return employees
