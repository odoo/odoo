from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    applicant_ids = fields.One2many(
        comodel_name="hr.applicant",
        inverse_name="employee_id",
        string="Applicants",
        groups="hr.group_hr_user",
    )

    def _get_partner_count_depends(self):
        return super()._get_partner_count_depends() + ["applicant_ids"]

    def _get_related_partners(self):
        partners = super()._get_related_partners()
        return partners | self.sudo().applicant_ids.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for employee_sudo in employees.sudo():
            if employee_sudo.applicant_ids:
                employee_sudo.applicant_ids._message_log_with_view(
                    "hr_recruitment.applicant_hired_template",
                    render_values={"applicant": employee_sudo.applicant_ids},
                )
        return employees
