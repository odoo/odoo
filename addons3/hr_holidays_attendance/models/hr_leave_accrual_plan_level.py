# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccrualPlanLevel(models.Model):
    _inherit = "hr.leave.accrual.level"

    frequency_hourly_source = fields.Selection(
        selection=[
            ('calendar', 'Calendar'),
            ('attendance', 'Attendances')
        ],
        default='calendar',
        compute='_compute_frequency_hourly_source',
        store=True,
        readonly=False,
        help="If the source is set to Calendar, the amount of worked hours will be computed from employee calendar and time off (if the plan is based on worked time). Otherwise, the amount of worked hours will be based on Attendance records.")

    @api.depends('accrued_gain_time')
    def _compute_frequency_hourly_source(self):
        for level in self:
            if level.accrued_gain_time == 'start':
                level.frequency_hourly_source = 'calendar'
