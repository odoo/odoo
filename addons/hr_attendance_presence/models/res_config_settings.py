# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_presence_control_attendance = fields.Boolean(string="According to the Attendance module", config_parameter='hr_presence.hr_presence_control_attendance')
