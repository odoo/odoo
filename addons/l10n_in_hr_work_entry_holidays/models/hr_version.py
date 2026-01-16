# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time, timedelta
import pytz

from odoo import models, Command


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def _get_version_work_entries_values(self, date_start, date_stop):
        """
            Generate work entry values for the given date range for Indian payroll, specifically for sandwich leaves.
            It will create work entries for the days that are covered by sandwich leaves(also linked sandwich leaves).
            Work entries of public holiday will be updated to the leave work entry type.
        """
        work_entry_values = super()._get_version_work_entries_values(date_start, date_stop)
        in_versions = self.filtered(lambda c: c.company_id.country_id.code == 'IN')
        if not in_versions:
            return work_entry_values

        holiday_status_cache = {}
        start_dt = self._ensure_timezone(date_start)
        end_dt = self._ensure_timezone(date_stop)
        employees = in_versions.mapped('employee_id')
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
        sandwich_leaves = sum(leaves_by_employee.values(), self.env['hr.leave'])
        indian_leaves, leaves_dates_by_employee, public_holidays_dates_by_company = sandwich_leaves._l10n_in_prepare_sandwich_context()
        span_data = indian_leaves._l10n_in_compute_sandwich_spans(leaves_dates_by_employee, public_holidays_dates_by_company)
        if not span_data:
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

            # Get start time from attendance, fallback to 08:00
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
                span_info = span_data.get(leave.id)
                if not span_info or not span_info['has_non_working']:
                    continue

                leave_start_date = span_info['start']
                leave_end_date = span_info['end']
                if leave_end_date < start_dt.date() or leave_start_date > end_dt.date():
                    continue
                leave_start_dt = self._ensure_timezone(datetime.combine(leave_start_date, time.min))
                leave_end_dt = self._ensure_timezone(datetime.combine(leave_end_date, time.max))
                filtered_public_holidays = public_holidays.filtered(lambda public_holiday:
                    (not leave.company_id or public_holiday.company_id == leave.company_id) and
                    (not public_holiday.calendar_id or public_holiday.calendar_id == version_calendar_id) and
                    public_holiday.date_from >= leave_start_dt.replace(tzinfo=None) and
                    public_holiday.date_to <= leave_end_dt.replace(tzinfo=None)
                )

                # Update work entries for public holidays
                span_public_holiday_dates = {
                    holiday.date_from.astimezone(tz).date()
                    for holiday in filtered_public_holidays
                }
                self._update_public_holiday_work_entry_values(
                    employee, leave, leave_work_entry_type, leave_start_dt, leave_end_dt, work_entry_values, filtered_public_holidays, span_public_holiday_dates)
                leave_dates = {
                    leave_start_date + timedelta(days=i)
                    for i in range((leave_end_date - leave_start_date).days + 1)
                }
                missing_dates = leave_dates - attendance_dates
                for missing_date in missing_dates:
                    work_entry_start = datetime.combine(missing_date, working_start_time_utc)
                    work_entry_stop = work_entry_start + timedelta(hours=version_calendar_id.hours_per_day)
                    work_entry_values.append({
                        'name': "%s: %s" % (leave_work_entry_type.name or self.env._('Undefined Type'), employee.name),
                        'date': missing_date,
                        'duration': version_calendar_id.hours_per_day,
                        'date_start': work_entry_start,
                        'date_stop': work_entry_stop,
                        'l10n_in_sandwich_non_working': True,
                        'work_entry_type_id': leave_work_entry_type.id,
                        'employee_id': employee.id,
                        'company_id': version.company_id.id,
                        'state': 'draft',
                        'version_id': version.id,
                        'leave_ids': [Command.set(leave.ids)],
                    })
        return work_entry_values

    def _ensure_timezone(self, dt):
        if not dt.tzinfo:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(pytz.utc)

    def _update_public_holiday_work_entry_values(self, employee, leave, leave_work_entry_type, leave_start_dt,
                                                 leave_end_dt, work_entry_values, public_holidays, public_holiday_dates):
        # This method will update the work entry of public holidays
        # And the work entry values for public holidays in the work_entry_values
        if holiday_work_entry_type_ids := public_holidays.work_entry_type_id.ids:
            leave_start_date = leave_start_dt.date()
            leave_end_date = leave_end_dt.date()
            public_holidays_work_entries = self.env['hr.work.entry'].search([
                ('date', '>=', leave_start_date),
                ('date', '<=', leave_end_date),
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', 'in', holiday_work_entry_type_ids),
            ])
            public_holidays_work_entries.write({
                'work_entry_type_id': leave_work_entry_type.id,
                'leave_ids': [Command.set(leave.ids)],
                'name': "%s: %s" % (leave_work_entry_type.name or self.env._('Undefined Type'), employee.name),
            })
        work_enry_values_to_update = [
            work_entry for work_entry in work_entry_values
            if not work_entry.get('leave_ids')
            and (entry_date := work_entry.get('date') or (
                work_entry.get('date_start') and self._ensure_timezone(work_entry['date_start']).date()
            ))
            and leave_start_dt.date() <= entry_date <= leave_end_dt.date()
            and entry_date in public_holiday_dates
        ]
        if work_enry_values_to_update:
            update_values = {
                'work_entry_type_id': leave_work_entry_type.id,
                'leave_ids': [Command.set(leave.ids)],
                'name': "%s: %s" % (leave_work_entry_type.name or self.env._('Undefined Type'), employee.name),
            }
            for entry in work_enry_values_to_update:
                entry.update(update_values)

    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        # Skip calendar-based duration recomputation for generated sandwich non-working days
        if vals.get('l10n_in_sandwich_non_working'):
            return False
        return super()._generate_work_entries_postprocess_adapt_to_calendar(vals)

    def _generate_work_entries_postprocess(self, vals_list):
        vals_list = super()._generate_work_entries_postprocess(vals_list)
        for vals in vals_list:
            vals.pop('l10n_in_sandwich_non_working', None)
        return vals_list
