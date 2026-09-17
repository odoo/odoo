# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_presence_control_email_amount = fields.Integer(string="# emails to send")
    hr_presence_control_ip_list = fields.Char(string="Valid IP addresses")
    employee_properties_definition = fields.PropertiesDefinition('Employee Properties')
    hr_presence_control_login = fields.Boolean(string="Based on user status in system", default=True)
    hr_presence_control_email = fields.Boolean(string="Based on number of emails sent")
    hr_presence_control_ip = fields.Boolean(string="Based on IP Address")
    hr_presence_control_attendance = fields.Boolean(string="Based on attendances", default=lambda self: self._default_hr_presence_control_attendance())
    contract_expiration_notice_period = fields.Integer("Contract Expiry Notice Period", default=7)
    work_permit_expiration_notice_period = fields.Integer("Work Permit Expiry Notice Period", default=60)

    def _default_hr_presence_control_attendance(self):
        module = self.env['ir.module.module'].sudo().search([('name', '=', 'hr_attendance'), ('state', '=', 'installed')], limit=1)
        return bool(module)

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies.sudo()._create_work_location()
        return companies

    def _create_work_location(self):
        companies_without_work_location = self.filtered(
            lambda c: not self.env['hr.work.location'].sudo().search_count([('company_id', '=', c.id)], limit=1))
        if companies_without_work_location:
            vals_list = [company._prepare_work_location_values() for company in companies_without_work_location]
            self.env['hr.work.location'].sudo().create(vals_list)

    def _prepare_work_location_values(self):
        self.ensure_one()
        return {
            'name': _('Office'),
            'company_id': self.id,
            'location_type': 'office',
        }
