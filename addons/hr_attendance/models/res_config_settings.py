# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_attendance_use_pin = fields.Boolean(string='Employee PIN',
        implied_group="hr_attendance.group_hr_attendance_use_pin")
    count_attendance_extra_hours = fields.Boolean(string="Count Extra Hours",
        related="company_id.count_attendance_extra_hours", readonly=False)
    extra_hours_start_date = fields.Datetime(string="Extra Hours Starting Date",
        related="company_id.extra_hours_start_date", readonly=False)
