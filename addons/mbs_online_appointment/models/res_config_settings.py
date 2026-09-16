# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    account_sid = fields.Char(string="Account Sid", config_parameter="mbs_online_appointment.account_sid")
    auth_token = fields.Char(string="Auth token", config_parameter="mbs_online_appointment.auth_token")
    twilio_number = fields.Char(string="Twilio Number", config_parameter="mbs_online_appointment.twilio_number")