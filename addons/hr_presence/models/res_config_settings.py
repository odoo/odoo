# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_presence_control_login = fields.Boolean(string="the system login (User status on chat)", config_parameter='hr_presence.hr_presence_control_login')
    hr_presence_control_email = fields.Boolean(string="the amount of sent emails", config_parameter='hr_presence.hr_presence_control_email')
    hr_presence_control_ip = fields.Boolean(string="the IP address", config_parameter='hr_presence.hr_presence_control_ip')
    hr_presence_control_email_amount = fields.Integer(related="company_id.hr_presence_control_email_amount", readonly=False)
    hr_presence_control_ip_list = fields.Char(related="company_id.hr_presence_control_ip_list", readonly=False)
