# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time, UTC
from zoneinfo import ZoneInfo

from odoo import api, models
from odoo.fields import Command, Domain
from odoo.tools.date_utils import localized


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
                    result.append(('leave_ids', [Command.link(leave[2].holiday_id.id)]))
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

        interval_start = interval[0].astimezone(UTC).replace(tzinfo=None)
        interval_stop = interval[1].astimezone(UTC).replace(tzinfo=None)
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
        return res or (not 'work_entry_type_id' not in vals and vals.get('leave_ids'))

    @api.model
    def _get_work_entry_source_fields(self):
        return super()._get_work_entry_source_fields() + ['leave_ids']

    def _get_version_work_entries_values(self, date_start, date_stop):
        """
        This method is responsible for generating work entry values for employees who are on
        calendar-based leaves. It ensures that work entries are created even when an employee's
        leave overlaps with public holidays linked to their calendar.
        """
        work_entry_values = super()._get_version_work_entries_values(date_start, date_stop)
        if not self:
            return work_entry_values

        start_dt = localized(date_start) if not date_start.tzinfo else date_start.astimezone(UTC)
        end_dt = localized(date_stop) if not date_stop.tzinfo else date_stop.astimezone(UTC)

        leaves_by_employee = dict(self.env['hr.leave']._read_group(
            domain=[
                ('employee_id', '=', self.employee_id.ids),
                ('state', '=', 'validate'),
                ('date_from', '<=', end_dt.replace(tzinfo=None)),
                ('date_to', '>=', start_dt.replace(tzinfo=None)),
                ('holiday_status_id.count_days_as', '=', 'calendar')
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))

        if not leaves_by_employee:
            return work_entry_values

        existing_entries = {(vals['date_start'], vals['date_stop']) for vals in work_entry_values}
        public_holidays = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', self.company_id.ids),
            ('calendar_id', 'in', self.resource_calendar_id.ids + [False]),
            ('date_from', '<=', end_dt.replace(tzinfo=None)),
            ('date_to', '>=', start_dt.replace(tzinfo=None)),
        ])

        resources_per_tz = self._get_resources_per_tz()
        attendance_intervals_by_calendar = {
            calendar: calendar._attendance_intervals_batch(start_dt, end_dt, resources_per_tz=resources_per_tz)
            for calendar in self.resource_calendar_id
        }

        for version in self:
            employee = version.employee_id
            resource = employee.resource_id
            calendar = version.resource_calendar_id or version.company_id.resource_calendar_id
            tz = ZoneInfo(employee.tz)

            attendance_intervals = attendance_intervals_by_calendar.get(calendar, {}).get(resource.id, [])
            attendance_dates = {start.date() for start, *_ in attendance_intervals}

            working_start_time_utc = (
                min(start.time() for start, *_ in attendance_intervals)
                if attendance_intervals else time(8, 0)
            )

            for leave in leaves_by_employee.get(employee, []):
                leave_work_entry_type = leave.holiday_status_id.work_entry_type_id
                duration_by_date = {}

                leave_date_start = leave.date_from.date()
                leave_date_end = leave.date_to.date()
                hours_per_day = calendar.hours_per_day
                start_hour = working_start_time_utc.hour
                end_hour = start_hour + hours_per_day

                if leave.leave_type_request_unit == 'hour':
                    start_from = max(leave.request_hour_from, start_hour)
                    if leave_date_start == leave_date_end:
                        duration_by_date[leave_date_start] = max(
                            0,
                            min(end_hour, leave.request_hour_to) - start_from
                        )
                    else:
                        duration_by_date[leave_date_start] = max(0, end_hour - start_from)
                        end_to = min(leave.request_hour_to, end_hour)
                        duration_by_date[leave_date_end] = max(
                            0,
                            end_to - start_hour
                        )
                elif leave.leave_type_request_unit == 'half_day':
                    if leave.request_date_from_period == 'pm':
                        duration_by_date[leave_date_start] = hours_per_day // 2
                    else:
                        duration_by_date[leave_date_start] = hours_per_day
                    if leave.request_date_to_period == 'pm':
                        duration_by_date[leave_date_end] = hours_per_day
                    else:
                        duration_by_date[leave_date_end] = hours_per_day // 2

                if leave.holiday_status_id.include_public_holidays_in_duration:
                    start_date = leave.date_from
                    end_date = leave.date_to

                    for entry in work_entry_values:
                        entry_date = entry['date_start'].date()

                        if (
                            not entry.get('leave_id')
                            and employee.id == entry.get('employee_id')
                            and start_date <= entry['date_start'] <= end_date
                        ):
                            entry.update({
                                'work_entry_type_id': leave_work_entry_type.id,
                                'leave_ids': [leave.id],
                                'name': "%s: %s" % (leave_work_entry_type.name or self.env._('Undefined Type'), employee.name),
                                'duration': hours_per_day - duration_by_date.get(entry_date, 0),
                                'date': entry_date
                            })

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
                for missing_date in missing_dates:
                    duration = duration_by_date.get(missing_date) or calendar.hours_per_day

                    # Center the interval around 12:00 PM
                    center_dt = datetime.combine(missing_date, time(12, 0))
                    half_duration = timedelta(hours=duration / 2)

                    work_entry_start = center_dt - half_duration
                    work_entry_end = center_dt + half_duration

                    if (work_entry_start, work_entry_end) in existing_entries:
                        continue

                    work_entry_values.append({
                        'name': "%s: %s" % (
                            leave_work_entry_type.name or self.env._('Undefined Type'),
                            employee.name,
                        ),
                        'date_start': work_entry_start,
                        'date_stop': work_entry_end,
                        'duration': duration,
                        'date': missing_date,
                        'work_entry_type_id': leave_work_entry_type.id,
                        'employee_id': employee.id,
                        'company_id': version.company_id.id,
                        'version_id': version.id,
                        'leave_ids': [leave.id],
                    })
        return work_entry_values
