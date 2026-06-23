# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    applicant_ids = fields.One2many('hr.applicant', 'employee_id', 'Applicants', groups="hr.group_hr_user")
    applicant_name = fields.Char(compute="_compute_applicant_name", groups="hr.group_hr_user")

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
                employee_sudo.applicant_ids._message_log_with_view(
                    'hr_recruitment.applicant_hired_template',
                    render_values={'applicant': employee_sudo.applicant_ids}
                )
        return employees

    @api.depends('applicant_ids.partner_name')
    def _compute_applicant_name(self):
        for employee in self:
            if len(employee.applicant_ids) == 1:
                employee.applicant_name = employee.applicant_ids.partner_name
            else:
                employee.applicant_name = employee.name

    def action_open_applicant(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Applicant'),
            'res_model': 'hr.applicant',
            'view_mode': 'form',
            'res_id': self.applicant_ids.id,
            'target': 'current',
        }
