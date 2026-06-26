# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, timedelta

from odoo import models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    @staticmethod
    def _l10n_in_to_utc(dt):
        return dt.replace(tzinfo=UTC) if not dt.tzinfo else dt.astimezone(UTC)

    @classmethod
    def _l10n_in_get_entry_date(cls, work_entry_vals):
        if work_entry_vals.get('date'):
            return work_entry_vals['date']
        if work_entry_vals.get('date_start'):
            return cls._l10n_in_to_utc(work_entry_vals['date_start']).date()
        return False

    @staticmethod
    def _l10n_in_is_date_included_by_sandwich_policy(leave, check_date, public_holiday_dates):
        policy = leave.work_entry_type_id.l10n_in_sandwich_policy or 'full'
        is_weekend = not leave.resource_calendar_id._works_on_date(check_date)
        is_public_holiday = check_date in public_holiday_dates

        return (
            policy == "full"
            or (not is_weekend and not is_public_holiday)
            or (policy == "weekend" and is_weekend)
            or (policy == "public_holiday" and is_public_holiday)
        )

    @staticmethod
    def _l10n_in_is_non_working_sandwich_date(check_date, attendance_dates, public_holiday_dates):
        return check_date in public_holiday_dates or check_date not in attendance_dates

    def _l10n_in_get_sandwich_leaves_by_employee(self, start_dt, end_dt):
        grouped_leaves = self.env['hr.leave']._read_group(
            domain=[
                ('employee_id', 'in', self.employee_id.ids),
                ('state', '=', 'validate'),
                ('date_from', '<=', end_dt.replace(tzinfo=None)),
                ('date_to', '>=', start_dt.replace(tzinfo=None)),
                ('work_entry_type_id.l10n_in_is_sandwich_leave', '=', True),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        )

        leaves_per_employee_dict = dict(grouped_leaves)
        leaves_dates_by_employee = {}

        for employee, leaves in grouped_leaves:
            full_day_leaves = leaves.filtered(lambda leave: leave._l10n_in_is_full_day_request())
            if not full_day_leaves:
                continue
            leaves_dates_by_employee[employee] = {
                (leave.request_date_from + timedelta(days=offset)): leave
                for leave in leaves
                for offset in range((leave.request_date_to - leave.request_date_from).days + 1)
            }

        return leaves_dates_by_employee, leaves_per_employee_dict

    def _l10n_in_prepare_sandwich_span_data(self, leaves_per_employee_dict, leaves_dates_by_employee):
        sandwich_leaves = sum(leaves_per_employee_dict.values(), self.env['hr.leave'])
        indian_leaves, _, public_holiday_dates_by_company = sandwich_leaves._l10n_in_prepare_sandwich_context()
        span_data = indian_leaves._l10n_in_compute_sandwich_spans(
            leaves_dates_by_employee,
            public_holiday_dates_by_company,
        )
        return span_data, public_holiday_dates_by_company

    def _l10n_in_get_attendance_dates_by_employee(self, start_dt, end_dt):
        attendance_intervals_by_calendar = {
            calendar: calendar._attendance_intervals_batch(
                start_dt,
                end_dt,
                resources_per_tz=versions._get_resources_per_tz(),
            )
            for calendar, versions in self.grouped('resource_calendar_id').items()
        }

        attendance_dates_by_employee = {}
        for version in self:
            employee = version.employee_id
            calendar = version.resource_calendar_id
            resource = employee.resource_id

            attendance_intervals = attendance_intervals_by_calendar.get(calendar, {}).get(resource.id, [])
            attendance_dates_by_employee[employee.id] = {
                interval[0].date()
                for interval in attendance_intervals
            }

        return attendance_dates_by_employee

    def _l10n_in_prepare_existing_work_entries(self, result):
        updatable_entries_by_employee_date = defaultdict(lambda: defaultdict(list))
        occupied_dates_by_employee = defaultdict(set)

        for work_entry_vals in result:
            employee = work_entry_vals.get('employee_id')
            employee_id = employee.id if employee else False
            entry_date = self._l10n_in_get_entry_date(work_entry_vals)

            if not employee_id or not entry_date:
                continue

            occupied_dates_by_employee[employee_id].add(entry_date)

            if not work_entry_vals.get('leave_ids'):
                updatable_entries_by_employee_date[employee_id][entry_date].append(work_entry_vals)

        return updatable_entries_by_employee_date, occupied_dates_by_employee

    def _get_version_work_entries_values(self, date_start, date_stop):
        result = super()._get_version_work_entries_values(date_start, date_stop)
        in_versions = self.filtered(lambda version: version.company_id.country_id.code == 'IN')
        if not in_versions:
            return result

        start_dt = self._l10n_in_to_utc(date_start)
        end_dt = self._l10n_in_to_utc(date_stop)

        leaves_dates_by_employee, leaves_per_employee_dict = in_versions._l10n_in_get_sandwich_leaves_by_employee(start_dt, end_dt)
        if not leaves_dates_by_employee:
            return result

        span_data, public_holiday_dates_by_company = self._l10n_in_prepare_sandwich_span_data(leaves_per_employee_dict, leaves_dates_by_employee)
        if not span_data:
            return result

        attendance_dates_by_employee = in_versions._l10n_in_get_attendance_dates_by_employee(start_dt, end_dt)
        updatable_entries_by_employee_date, occupied_dates_by_employee = self._l10n_in_prepare_existing_work_entries(result)

        for version in in_versions:
            employee = version.employee_id
            employee_id = employee.id
            attendance_dates = attendance_dates_by_employee.get(employee_id, set())
            occupied_dates = occupied_dates_by_employee[employee_id]
            updatable_entries_by_date = updatable_entries_by_employee_date[employee_id]

            for leave in leaves_per_employee_dict.get(employee, self.env['hr.leave']):
                span_info = span_data.get(leave.id)
                if not span_info or not span_info.get('has_non_working'):
                    continue

                leave_start_date = max(span_info['start'], start_dt.date())
                leave_end_date = min(span_info['end'], end_dt.date())
                if leave_end_date < leave_start_date:
                    continue

                leave_work_entry_type = leave.work_entry_type_id
                public_holiday_per_company = public_holiday_dates_by_company.get(leave.company_id, set())
                for offset in range((leave_end_date - leave_start_date).days + 1):
                    span_date = leave_start_date + timedelta(days=offset)

                    if not self._l10n_in_is_date_included_by_sandwich_policy(leave, span_date, public_holiday_per_company):
                        continue

                    is_non_working_sandwich = self._l10n_in_is_non_working_sandwich_date(
                        span_date,
                        attendance_dates,
                        public_holiday_per_company,
                    )
                    if updatable_entries := updatable_entries_by_date.pop(span_date, []):
                        for work_entry_vals in updatable_entries:
                            work_entry_vals.update({
                                'work_entry_type_id': leave_work_entry_type,
                                'leave_ids': leave,
                                'l10n_in_is_sandwich_non_working': is_non_working_sandwich,
                            })
                        continue

                    if span_date in attendance_dates or span_date in occupied_dates:
                        continue

                    result.append({
                        'date': span_date,
                        'duration': version.resource_calendar_id.hours_per_day,
                        'work_entry_type_id': leave_work_entry_type,
                        'employee_id': employee,
                        'company_id': version.company_id,
                        'version_id': version,
                        'leave_ids': leave,
                        'l10n_in_is_sandwich_non_working': is_non_working_sandwich,
                    })
                    occupied_dates.add(span_date)
        return result
