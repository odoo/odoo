# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time
import pytz

from odoo import api, models
from odoo.fields import Domain


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
                result.append(('leave_id', leave[2].holiday_id.id))
        return result

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        # returns the work entry time related to the leave that
        # includes the whole interval.
        # Overriden in hr_work_entry_holiday to select the
        # global time off first (eg: Public Holiday > Home Working)
        self.ensure_one()
        if 'work_entry_type_id' in interval[2] and interval[2].work_entry_type_id.code in bypassing_codes:
            return interval[2].work_entry_type_id

        interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
        interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
        including_rcleaves = [l[2] for l in leaves if l[2] and interval_start >= l[2].date_from and interval_stop <= l[2].date_to]
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

    @api.model
    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        res = super()._generate_work_entries_postprocess_adapt_to_calendar(vals)
        return res or (not 'work_entry_type_id' not in vals and vals.get('leave_id'))

    def _ensure_timezone(self, dt):
        if not dt.tzinfo:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(pytz.utc)

    def _get_version_work_entries_values(self, date_start, date_stop):
        """
        This method is responsible for generating work entry values for employees who are on
        calendar-based leaves. It ensures that work entries are created even when an employee's
        leave overlaps with public holidays linked to their calendar.
        """
        work_entry_values = super()._get_version_work_entries_values(date_start, date_stop)
        if not self:
            return work_entry_values

        holiday_status_cache = {}

        start_dt = self._ensure_timezone(date_start)
        end_dt = self._ensure_timezone(date_stop)

        employees = self.mapped('employee_id')
        resources = employees.mapped('resource_id')
        calendars = self.mapped('resource_calendar_id')

        existing_entries = {(vals['date_start'], vals['date_stop']) for vals in work_entry_values}

        public_holidays = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', self.company_id.ids),
            ('calendar_id', 'in', calendars.ids + [False]),
            ('date_from', '<=', end_dt.replace(tzinfo=None)),
            ('date_to', '>=', start_dt.replace(tzinfo=None)),
        ])

        leaves_by_employee = dict(self.env['hr.leave']._read_group(
            domain=[
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'validate'),
                ('date_from', '<=', end_dt.replace(tzinfo=None)),
                ('date_to', '>=', start_dt.replace(tzinfo=None)),
                ('holiday_status_id.count_days_as', '=', 'calendar'),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))

        if not leaves_by_employee:
            return work_entry_values

        attendance_intervals_by_calendar = {
            calendar: calendar._attendance_intervals_batch(start_dt, end_dt, resources=resources, tz=pytz.timezone(calendar.tz))
            for calendar in calendars
        }

        for version in self:
            employee = version.employee_id
            resource = employee.resource_id
            calendar = version.resource_calendar_id
            tz = pytz.timezone(calendar.tz)

            attendance_intervals = list(attendance_intervals_by_calendar.get(calendar, {}).get(resource.id, []))
            attendance_dates = {interval[0].date() for interval in attendance_intervals}

            working_start_time_utc = (
                attendance_intervals[0][0].astimezone(pytz.utc).time() if attendance_intervals else time(8, 0)
            )

            for leave in leaves_by_employee.get(employee, []):
                holiday_status_id = leave.holiday_status_id.id
                if holiday_status_id not in holiday_status_cache:
                    holiday_status_cache[holiday_status_id] = leave.holiday_status_id.work_entry_type_id
                leave_work_entry_type = holiday_status_cache[holiday_status_id]

                if leave.holiday_status_id.include_public_holidays_in_duration:
                    # Update work entries for public holidays
                    self._update_public_holiday_work_entry_values(
                        employee, leave, leave_work_entry_type, work_entry_values)

                leave_dates = {
                    leave.date_from.date() + timedelta(days=i)
                    for i in range((leave.date_to - leave.date_from).days + 1)
                }

                public_holiday_dates = {
                    holiday.date_from.astimezone(tz).date()
                    for holiday in public_holidays
                    if (not leave.company_id or holiday.company_id == leave.company_id)
                    and (not holiday.calendar_id or holiday.calendar_id == calendar)
                }

                missing_dates = leave_dates - attendance_dates - public_holiday_dates
                work_entry_values.extend(
                    {
                        'name': "%s: %s" % (leave_work_entry_type.name or self.env._('Undefined Type'), employee.name),
                        'date_start': work_entry_start,
                        'date_stop': work_entry_start + timedelta(hours=calendar.hours_per_day),
                        'work_entry_type_id': leave_work_entry_type.id,
                        'employee_id': employee.id,
                        'company_id': version.company_id.id,
                        'version_id': version.id,
                        'state': 'draft',
                        'leave_id': leave.id,
                    } for missing_date in missing_dates
                    if (
                        work_entry_start := datetime.combine(missing_date, working_start_time_utc),
                        work_entry_start + timedelta(hours=calendar.hours_per_day)
                    ) not in existing_entries
                )

        return work_entry_values

    def _update_public_holiday_work_entry_values(self, employee, leave, leave_work_entry_type, work_entry_values):
        # Update the work entry values for public holidays in the work_entry_values
        start_date = leave.date_from.date()
        end_date = leave.date_to.date()

        update_values = {
            'work_entry_type_id': leave_work_entry_type.id,
            'leave_id': leave.id,
            'name': "%s: %s" % (leave_work_entry_type.name or self.env._('Undefined Type'), employee.name),
        }

        for entry in work_entry_values:
            if (
                not entry.get('leave_id')
                and employee.id == entry.get('employee_id')
                and start_date <= entry['date_start'].date() <= end_date
            ):
                entry.update(update_values)
