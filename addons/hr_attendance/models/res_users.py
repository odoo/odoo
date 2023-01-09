# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class User(models.Model):
    _inherit = ['res.users']

    hours_last_month = fields.Float(related='employee_id.hours_last_month')
    hours_last_month_display = fields.Char(related='employee_id.hours_last_month_display')
    attendance_state = fields.Selection(related='employee_id.attendance_state')
    last_check_in = fields.Datetime(related='employee_id.last_attendance_id.check_in')
    last_check_out = fields.Datetime(related='employee_id.last_attendance_id.check_out')
    total_overtime = fields.Float(related='employee_id.total_overtime')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'hours_last_month',
            'hours_last_month_display',
            'attendance_state',
            'last_check_in',
            'last_check_out',
            'total_overtime'
        ]
