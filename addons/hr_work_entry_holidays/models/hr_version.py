# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz
from dateutil.rrule import DAILY, rrule

from odoo import api, models
from odoo.fields import Domain
from odoo.tools import float_is_zero
from odoo.tools.intervals import Intervals


class HrVersion(models.Model):
    _inherit = 'hr.version'
    _description = 'Employee Contract'

    # override to add work_entry_type from leave
    def _get_leave_work_entry_type(self, leave):
        if leave.holiday_id:
            return leave.holiday_id.holiday_status_id.work_entry_type_id
        else:
            return leave.work_entry_type_id

    def _get_more_vals_leave_interval(self, interval, leaves):
        result = super()._get_more_vals_leave_interval(interval, leaves)
        for leave in leaves:
            if interval[0] >= leave[0] and interval[1] <= leave[1]:
                if leave[2].holiday_id.id:
                    result.append(('leave_id', leave[2].holiday_id.id))
                    break
        return result

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        # returns the work entry time related to the leave that
        # includes the whole interval.
        # Overriden in hr_work_entry_holiday to select the
        # global time off first (eg: Public Holiday > Home Working)
        self.ensure_one()
        if 'work_entry_type_id' in interval[2]:
            work_entry_types = interval[2].work_entry_type_id
            if work_entry_types and work_entry_types[:1].code in bypassing_codes:
                return work_entry_types[:1]

        interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
        interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
        including_rcleaves = [l[2] for l in leaves if l[2] and interval_start < l[2].date_to and interval_stop > l[2].date_from]
        including_global_rcleaves = [l for l in including_rcleaves if not l.holiday_id]
        including_holiday_rcleaves = [l for l in including_rcleaves if l.holiday_id]
        rc_leave = False

        # Example: In CP200: Long term sick > Public Holidays (which is global)
        if bypassing_codes:
            bypassing_rc_leave = [l for l in including_holiday_rcleaves if l.holiday_id.holiday_status_id.work_entry_type_id.code in bypassing_codes]
        else:
            bypassing_rc_leave = []

        if bypassing_rc_leave:
            rc_leave = bypassing_rc_leave[0]
        elif including_global_rcleaves:
            rc_leave = including_global_rcleaves[0]
        elif including_holiday_rcleaves:
            rc_leave = including_holiday_rcleaves[0]
        if rc_leave:
            return self._get_leave_work_entry_type_dates(rc_leave, interval_start, interval_stop, self.employee_id)
        return self.env.ref('hr_work_entry.work_entry_type_leave')

    def _get_sub_leave_domain(self):
        # see https://github.com/odoo/enterprise/pull/15091
        return super()._get_sub_leave_domain() | Domain('holiday_id.employee_id', 'in', self.employee_id.ids)

    def _get_duration_based_real_leaves(self, start_dt, end_dt, attendances, leaves, worked_leaves):
        calendar = self.resource_calendar_id
        if not calendar.duration_based:
            return super()._get_duration_based_real_leaves(
                start_dt, end_dt, attendances, leaves, worked_leaves
            )
        tz = pytz.timezone(calendar.tz)
        start_day = tz.localize(datetime.combine(start_dt.astimezone(tz).date(), time.min))
        last_day = end_dt.astimezone(tz)
        duration_intervals = []
        for current_day in rrule(DAILY, dtstart=start_day, until=last_day - timedelta(microseconds=1)):
            if calendar._works_on_date(current_day.date()):
                duration_intervals.append(
                    (current_day, current_day + timedelta(days=1), leaves)
                )
        duration_based_days = Intervals(duration_intervals, keep_distinct=True)
        real_leaves = (leaves & duration_based_days) | (attendances & (leaves - duration_based_days))
        real_worked_leaves = (
            (worked_leaves & duration_based_days) | (attendances & (worked_leaves - duration_based_days))
        ) - real_leaves
        return real_leaves, real_worked_leaves

    def _get_duration_based_real_attendances(self, start_dt, end_dt, attendances, leaves, worked_leaves):
        """ The schedule of each day is shortened by the hours of leave taken that day,
        wherever in the day the leave was taken. Anything else (check-ins, overtime, ...)
        is handled as usual by _get_real_attendances. """
        calendar = self.resource_calendar_id
        if not (calendar.duration_based and self.has_static_work_entries()):
            return super()._get_duration_based_real_attendances(start_dt, end_dt, attendances, leaves, worked_leaves)
        tz = pytz.timezone(calendar.tz)
        start_day = tz.localize(datetime.combine(start_dt.astimezone(tz).date(), time.min))
        last_day = end_dt.astimezone(tz)
        resource = self.employee_id.resource_id
        schedule_intervals = calendar._attendance_intervals_batch(
            start_day, tz.localize(datetime.combine(last_day.date(), time.max)), resources=resource, tz=tz,
        )[resource.id] & Intervals([(start_dt, end_dt, self.env['resource.calendar.attendance'])])
        day_windows_intervals = Intervals([
            (current_day, current_day + timedelta(days=1), self.env['resource.calendar.leaves'])
            for current_day in rrule(DAILY, dtstart=start_day, until=last_day - timedelta(microseconds=1))
        ], keep_distinct=True)

        leave_hours_by_day = defaultdict(float)
        for interval_start, interval_stop, interval_leaves in (leaves | worked_leaves) & day_windows_intervals:
            current_day = interval_start.astimezone(tz).date()
            chunk_hours = (interval_stop - interval_start).total_seconds() / 3600
            for leave_record in interval_leaves:
                holiday = leave_record.holiday_id
                if (
                    holiday and holiday.request_unit_half
                    and holiday.request_date_from != holiday.request_date_to
                    and current_day in (holiday.request_date_from, holiday.request_date_to)
                ):
                    is_half = (
                        (current_day == holiday.request_date_from and holiday.request_date_from_period == 'pm')
                        or (current_day == holiday.request_date_to and holiday.request_date_to_period == 'am')
                    )
                    day_hours = sum(calendar._get_duration_based_day_attendances(current_day).mapped('duration_hours'))
                    chunk_hours = day_hours * 0.5 if is_half else day_hours
                    break
            leave_hours_by_day[current_day] += chunk_hours

        schedule_by_day = defaultdict(list)
        for interval in schedule_intervals:
            schedule_by_day[interval[0].astimezone(tz).date()].append(interval)
        other_attendances = [interval for interval in attendances if interval[2]._name != 'resource.calendar.attendance']

        schedule_attendances = []
        for day, day_schedule in schedule_by_day.items():
            hours_to_remove = leave_hours_by_day[day]
            for start, stop, record in day_schedule:
                interval_hours = (stop - start).total_seconds() / 3600
                if hours_to_remove >= interval_hours:
                    hours_to_remove -= interval_hours
                else:
                    schedule_attendances.append((start + timedelta(hours=hours_to_remove), stop, record))
                    hours_to_remove = 0.0
        return Intervals(schedule_attendances, keep_distinct=True) | self._get_real_attendances(
            Intervals(other_attendances, keep_distinct=True), leaves, worked_leaves)

    @api.model
    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        res = super()._generate_work_entries_postprocess_adapt_to_calendar(vals)
        return res or (not 'work_entry_type_id' not in vals and vals.get('leave_id'))

    @api.model
    def _generate_work_entries_postprocess(self, vals_list):
        result = super()._generate_work_entries_postprocess(vals_list)
        remaining_hours_by_day = {}
        for vals in result:
            calendar = self.env['hr.version'].browse(vals['version_id']).resource_calendar_id
            if not calendar.duration_based or not self._generate_work_entries_postprocess_adapt_to_calendar(vals):
                continue
            day_hours = sum(calendar._get_duration_based_day_attendances(vals['date']).mapped('duration_hours'))
            leave = self.env['hr.leave'].browse(vals.get('leave_id'))
            if (
                leave.request_unit_half
                and leave.request_date_from != leave.request_date_to
                and vals['date'] in (leave.request_date_from, leave.request_date_to)
            ):
                is_half = (
                    (vals['date'] == leave.request_date_from and leave.request_date_from_period == 'pm')
                    or (vals['date'] == leave.request_date_to and leave.request_date_to_period == 'am')
                )
                vals['duration'] = day_hours * 0.5 if is_half else day_hours
            # A day can't hold more leave than its configured hours
            day_key = (vals['version_id'], vals['date'])
            remaining_hours = remaining_hours_by_day.get(day_key, day_hours)
            vals['duration'] = min(vals['duration'], remaining_hours)
            remaining_hours_by_day[day_key] = remaining_hours - vals['duration']
        return [vals for vals in result if not float_is_zero(vals['duration'], 3)]
