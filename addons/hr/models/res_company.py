# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_presence_control_email_amount = fields.Integer(string="# emails to send")
    hr_presence_control_ip_list = fields.Char(string="Valid IP addresses")
    employee_properties_definition = fields.PropertiesDefinition('Employee Properties')
    hr_presence_control_login = fields.Boolean(string="Based on user status in system", default=True)
    hr_presence_control_email = fields.Boolean(string="Based on number of emails sent")
    hr_presence_control_ip = fields.Boolean(string="Based on IP Address")
    hr_presence_control_attendance = fields.Boolean(string="Based on attendances")

    def _get_session_info(self, allowed_company_ids):
        res = super()._get_session_info(allowed_company_ids)
        res.update({
            'country_code': self.country_id.code
        })
        return res
