# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import float_compare
from odoo import models, fields, api


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'full_time_required_hours' in fields and not res.get('full_time_required_hours'):
            company_id = res.get('company_id', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            res['full_time_required_hours'] = company.resource_calendar_id.full_time_required_hours
        return res

    hours_per_week = fields.Float(compute="_compute_hours_per_week", string="Hours per Week", store=True)
    is_fulltime = fields.Boolean(compute='_compute_is_fulltime', string="Is Full Time")
    work_time_rate = fields.Float(string='Work Time Rate', compute='_compute_work_time_rate', help='Work time rate versus full time working schedule, should be between 0 and 100 %.')

    @api.depends('attendance_ids.hour_from', 'attendance_ids.hour_to', 'attendance_ids.work_entry_type_id.is_leave')
    def _compute_hours_per_week(self):
        for calendar in self:
            sum_hours = sum(
                (a.hour_to - a.hour_from) for a in calendar.attendance_ids if a.day_period != 'lunch' and not a.work_entry_type_id.is_leave)
            calendar.hours_per_week = sum_hours / 2 if calendar.two_weeks_calendar else sum_hours

    def _get_days_per_week(self):
        # Returns the number of days per week during which the employee is working
        # For examples
        # 38h / weeks -> 5 days
        # 19h / weeks (M/T/Wam) -> 3 days
        # 19h / weeks (Mam/Tam/Wam/Tam/Fam) -> 5 days
        self.ensure_one()
        if self.two_weeks_calendar:
            return 5 * self.work_time_rate / 100
        return len(set(self.attendance_ids.filtered(
            lambda a: a.day_period != 'lunch' and not a.work_entry_type_id.is_leave).mapped('dayofweek')))

    def _compute_is_fulltime(self):
        for calendar in self:
            calendar.is_fulltime = not float_compare(calendar.full_time_required_hours, calendar.hours_per_week, 3)

    @api.depends('hours_per_week', 'full_time_required_hours', 'attendance_ids.work_entry_type_id')
    def _compute_work_time_rate(self):
        for calendar in self:
            if not calendar.hours_per_week:
                calendar.work_time_rate = calendar.hours_per_week
            else:
                if calendar.full_time_required_hours:
                    calendar.work_time_rate = calendar.hours_per_week / calendar.full_time_required_hours * 100
                else:
                    calendar.work_time_rate = calendar.hours_per_week / calendar.hours_per_week * 100
