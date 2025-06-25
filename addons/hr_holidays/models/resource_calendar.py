# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import fields, models
from odoo.fields import Domain
from odoo.tools.intervals import Intervals


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    associated_leaves_count = fields.Integer("Time Off Count", compute='_compute_associated_leaves_count')
    global_leave_ids = fields.Many2many('hr.leave.public.holiday', 'calendar_public_holiday_rel', 'calendar_id', 'leave_id',
        string='Global Time Off')

    def _compute_associated_leaves_count(self):
        leaves_read_group = self.env['hr.leave.public.holiday']._read_group(
            [('resource_calendar_ids', 'in', self.ids)],
            ['resource_calendar_ids'],
            ['__count'],
        )
        result = {calendar.id if calendar else 'global': count for calendar, count in leaves_read_group}
        global_leave_count = result.get('global', 0)
        for calendar in self:
            calendar.associated_leaves_count = result.get(calendar.id, 0) + global_leave_count

    def _public_holidays_batch(self, start_dt, end_dt, domain=None):
        dates_domain = [
            ('date_from', '<=', end_dt.astimezone(pytz.utc).replace(tzinfo=None)),
            ('date_to', '>=', start_dt.astimezone(pytz.utc).replace(tzinfo=None)),
        ]
        if not domain:
            domain = dates_domain
        else:
            domain = Domain.AND([domain, dates_domain])

        return self.env['hr.leave.public.holiday'].search(domain)

    def _public_holidays_interval_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, any_calendar=False):

        if not domain:
            domain = []

        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]

        if not any_calendar:
            domain = Domain.AND([domain, [('resource_calendar_ids', 'in', [False] + self.ids)]])

        public_holidays = self._public_holidays_batch(start_dt, end_dt, domain=domain)
        tz_dates = {}
        public_holidays_Intervals = list()
        for leave in public_holidays:
            leave_date_from = leave.date_from
            leave_date_to = leave.date_to
            tz = tz or pytz.timezone(self.tz)
            if (tz, start_dt) in tz_dates:
                start = tz_dates[tz, start_dt]
            else:
                start = start_dt.astimezone(tz)
                tz_dates[tz, start_dt] = start
            if (tz, end_dt) in tz_dates:
                end = tz_dates[tz, end_dt]
            else:
                end = end_dt.astimezone(tz)
                tz_dates[tz, end_dt] = end
            dt0 = leave_date_from.astimezone(tz)
            dt1 = leave_date_to.astimezone(tz)
            public_holidays_Intervals.append((max(start, dt0), min(end, dt1), leave))

        result = {}
        for resource in resources_list:
            resource_company = resource.company_id
            resource_work_address = resource.work_location_id.address_id
            resource_working_hours = resource.calendar_id
            resource_country = resource_work_address.country_id if resource_work_address else False
            resource_public_holidays = [(start, end, self.env['resource.calendar.leaves']) for start, end, leave in public_holidays_Intervals
                                        if (not leave.company_id or leave.company_id == resource_company) and
                                        (not leave.work_address_ids or resource_work_address in leave.work_address_ids) and
                                        (not leave.country_id or leave.country_id == resource_country) and
                                        (not leave.resource_calendar_ids or resource_working_hours in leave.resource_calendar_ids)]
            result[resource.id] = Intervals(resource_public_holidays)
        return result

    def _leave_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, any_calendar=False):
        base = super()._leave_intervals_batch(start_dt, end_dt, resources=resources, domain=domain, tz=tz, any_calendar=any_calendar)
        public_holidays_intervals = self._public_holidays_interval_batch(start_dt, end_dt, resources=resources, tz=tz, any_calendar=any_calendar)
        for resource_id in public_holidays_intervals:
            if resource_id not in base:
                base[resource_id] = Intervals()
            base[resource_id] |= public_holidays_intervals[resource_id]
        return base
