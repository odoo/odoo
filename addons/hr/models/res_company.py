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
    contract_expiration_notice_period = fields.Integer("Contract Expiry Notice Period", default=7)
    work_permit_expiration_notice_period = fields.Integer("Work Permit Expiry Notice Period", default=60)
