# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BaseConfigSettings(models.TransientModel):
    _name = 'attendance.config.settings'
    _inherit = 'res.config.settings'

    group_attendance_use_pin = fields.Boolean(string='Employee PIN',
        implied_group="hr_attendance.group_hr_attendance_use_pin")
    module_hr_timesheet = fields.Boolean(string='Timesheets')
    module_hr_holidays = fields.Boolean(string='Leave Management')
