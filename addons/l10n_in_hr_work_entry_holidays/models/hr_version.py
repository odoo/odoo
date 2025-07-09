# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time, timedelta
from itertools import count
import pytz

from odoo import models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def _get_version_work_entries_values(self, date_start, date_stop):
        # It will be list of dict that has all the values to create work entries
        work_entry_values = super()._get_version_work_entries_values(date_start, date_stop)
        in_versions = self.filtered(lambda c: c.company_id.country_id.code == 'IN')
        if not in_versions:
            return work_entry_values

        holiday_status_cache = {}
        start_dt = self._ensure_timezone(date_start)
        end_dt = self._ensure_timezone(date_stop)
        employees = in_versions.mapped('employee_id')
        existing_entries = {(vals['date_start'], vals['date_stop']) for vals in work_entry_values}
        public_holidays = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', in_versions.company_id.ids),
            ('calendar_id', 'in', in_versions.resource_calendar_id.ids + [False]),
        ])
        leaves_by_employee = dict(self.env['hr.leave']._read_group(
            domain=[
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'validate'),
                ('date_from', '<=', end_dt.replace(tzinfo=None)),
                ('date_to', '>=', start_dt.replace(tzinfo=None)),
                ('l10n_in_contains_sandwich_leaves', '=', True),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))
        if not leaves_by_employee:
            return work_entry_values

        resources = in_versions.mapped('employee_id.resource_id')
        attendance_intervals_by_calendar = {
            calendar: calendar._attendance_intervals_batch(
            start_dt, end_dt, resources=resources, tz=pytz.timezone(calendar.tz))
            for calendar in in_versions.mapped('resource_calendar_id')
        }

        for version in in_versions:
            employee = version.employee_id
            version_calendar_id = version.resource_calendar_id
            resource = employee.resource_id
            tz = pytz.timezone(version_calendar_id.tz)
            attendance_intervals = list(attendance_intervals_by_calendar.get(version_calendar_id).get(resource.id, []))
            working_start_time_utc = (
                attendance_intervals[0][0].astimezone(pytz.utc).time()
                if attendance_intervals else time(8, 0)
            )
            attendance_dates = {interval[0].date() for interval in attendance_intervals}

            for leave in leaves_by_employee[employee]:
                holiday_status_id = leave.holiday_status_id.id
                if holiday_status_id not in holiday_status_cache:
                    holiday_status_cache[holiday_status_id] = leave.holiday_status_id.work_entry_type_id
                leave_work_entry_type = holiday_status_cache[holiday_status_id]
                leave_start_dt, leave_end_dt = self._adjust_leave_dates(leave, start_dt, end_dt, tz, version_calendar_id)
                filtered_public_holidays = public_holidays.filtered(lambda public_holiday:
                    (not leave.company_id or public_holiday.company_id == leave.company_id) and
                    (not public_holiday.calendar_id or public_holiday.calendar_id == version_calendar_id) and
                    public_holiday.date_from >= leave_start_dt.replace(tzinfo=None) and
                    public_holiday.date_to <= leave_end_dt.replace(tzinfo=None)
                )

                self._update_public_holiday_work_entry_values(
                    employee, leave, leave_work_entry_type, leave_start_dt, leave_end_dt, work_entry_values, filtered_public_holidays)
                leave_dates = {
                    leave_start_dt.date() + timedelta(days=i)
                    for i in range((leave_end_dt - leave_start_dt).days + 1)
                }
                public_holiday_dates = {
                    holiday.date_from.date()
                    for holiday in filtered_public_holidays
                } if leave.linked_sandwich_leave_id else set()
                missing_dates = leave_dates - attendance_dates - public_holiday_dates
                work_entry_values.extend(
                    {
                        'name': "%s: %s" % (leave_work_entry_type.name or self.env._('Undefined Type'), employee.name),
                        'date_start': work_entry_start,
                        'date_stop': work_entry_start + timedelta(hours=version_calendar_id.hours_per_day),
                        'work_entry_type_id': leave_work_entry_type.id,
                        'employee_id': employee.id,
                        'company_id': version.company_id.id,
                        'state': 'draft',
                        'version_id': version.id,
                        'leave_id': leave.id,
                    } for missing_date in missing_dates
                    if (
                        work_entry_start := datetime.combine(missing_date, working_start_time_utc),
                        work_entry_start + timedelta(hours=version_calendar_id.hours_per_day)
                    ) not in existing_entries
                )
        return work_entry_values

    def _is_non_working_day(self, calendar_id, date):
        return not calendar_id._works_on_date(date)

    def _get_working_day(self, calendar_id, date, step):
        return next(
            filter(lambda d: not self._is_non_working_day(calendar_id, d),
                (date + timedelta(days=i * step) for i in count()))
        )

    def _ensure_timezone(self, dt):
        if not dt.tzinfo:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(pytz.utc)

    def _adjust_leave_dates(self, leave, start_dt, end_dt, tz, version_calendar_id):
        leave_start_dt = max(start_dt, self._ensure_timezone(leave.date_from))
        leave_end_dt = min(end_dt, self._ensure_timezone(leave.date_to))

        if linked_leave := leave.linked_sandwich_leave_id:
            leave_start_dt = min(leave_start_dt, self._ensure_timezone(linked_leave.date_to))
            leave_end_dt = max(leave_end_dt, self._ensure_timezone(linked_leave.date_from))
            if not linked_leave.has_edge_public_leave:
                leave_start_dt += timedelta(days=1)
                leave_end_dt += timedelta(days=-1)
        elif self._is_non_working_day(version_calendar_id, leave_start_dt) and self._is_non_working_day(version_calendar_id, leave_end_dt):
            leave_start_dt = self._get_working_day(version_calendar_id, leave_start_dt, 1)
            leave_end_dt = self._get_working_day(version_calendar_id, leave_end_dt, -1)
        leave_start_dt = datetime.combine(leave_start_dt.date(), time.min)
        leave_end_dt = datetime.combine(leave_end_dt.date(), time.max)
        return leave_start_dt, leave_end_dt

    def _update_public_holiday_work_entry_values(self, employee, leave, leave_work_entry_type, leave_start_dt,
                                                 leave_end_dt, work_entry_values, public_holidays):
        # This method will update the work entry of public holidays
        # And the work entry values for public holidays in the work_entry_values
        if holiday_work_entry_type_ids := public_holidays.work_entry_type_id.ids:
            public_holidays_work_entries = self.env['hr.work.entry'].search([
                ('date_start', '>=', leave_start_dt),
                ('date_stop', '<=', leave_end_dt),
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', 'in', holiday_work_entry_type_ids),
            ])
            public_holidays_work_entries.write({
                'work_entry_type_id': leave_work_entry_type.id,
                'leave_id': leave.id,
                'name': "%s: %s" % (leave_work_entry_type.name or self.env._('Undefined Type'), employee.name),
            })
        work_enry_values_to_update = [
            work_entry for work_entry in work_entry_values
            if not work_entry.get('leave_id') and (
                (
                    leave.linked_sandwich_leave_id and
                    leave_start_dt.date() <= work_entry['date_start'].date() <= leave_end_dt.date()
                ) or (
                    not leave.linked_sandwich_leave_id and
                    leave_start_dt.date() < work_entry['date_start'].date() < leave_end_dt.date()
                )
            )
        ]
        if work_enry_values_to_update:
            update_values = {
                'work_entry_type_id': leave_work_entry_type.id,
                'leave_id': leave.id,
                'name': "%s: %s" % (leave_work_entry_type.name or self.env._('Undefined Type'), employee.name),
            }
            for entry in work_enry_values_to_update:
                entry.update(update_values)
