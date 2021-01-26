# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_attendance_use_pin = fields.Boolean(string='Employee PIN',
        implied_group="hr_attendance.group_hr_attendance_use_pin")
    hr_attendance_overtime = fields.Boolean(string="Count Extra Hours", compute='_compute_extra_hours',
                                            inverse='_inverse_extra_hours', readonly=False)
    overtime_start_date = fields.Date(string="Extra Hours Starting Date", compute='_compute_extra_hours',
                                            inverse='_inverse_extra_hours', readonly=False)

    @api.depends('company_id')
    def _compute_extra_hours(self):
        for setting in self:
            setting.hr_attendance_overtime = setting.company_id.hr_attendance_overtime
            setting.overtime_start_date = setting.company_id.overtime_start_date

    def _inverse_extra_hours(self):
        # Done this way to have both values written at the same time...
        for setting in self:
            setting.company_id.write({
                'hr_attendance_overtime': setting.hr_attendance_overtime,
                'overtime_start_date': setting.overtime_start_date if setting.hr_attendance_overtime else False
            })
