# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

from odoo import models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def _l10n_in_search_sandwich_leaves(self, employees, date_from, date_to):
        return self.env['hr.leave'].search([
            ('employee_id', 'in', employees.ids),
            ('state', '=', 'validate'),
            ('work_entry_type_id.l10n_in_is_sandwich_leave', '=', True),
            ('request_date_to', '>=', date_from),
            ('request_date_from', '<=', date_to),
        ])

    def _get_version_work_entries_values(self, date_start, date_stop):
        result = super()._get_version_work_entries_values(date_start, date_stop)
        in_versions = self.filtered(lambda version: version.company_id.country_id.code == 'IN')
        if not in_versions:
            return result

        start_dt = date_start.replace(tzinfo=UTC) if not date_start.tzinfo else date_start.astimezone(UTC)
        end_dt = date_stop.replace(tzinfo=UTC) if not date_stop.tzinfo else date_stop.astimezone(UTC)

        # A sandwich span extends at most 30 days of non-working days past its leave, and the
        # links (and their own links) used to compute it may lie outside the generation window:
        # only load the leaves close enough to the window to have an effect on it.
        margin = timedelta(days=31)
        leaves = self._l10n_in_search_sandwich_leaves(
            in_versions.employee_id, start_dt.date() - 2 * margin, end_dt.date() + 2 * margin,
        )
        if leaves:
            # Links of the linked leaves are searched from their far edge.
            widened_from = min(leaves.mapped('request_date_from')) - margin
            widened_to = max(leaves.mapped('request_date_to')) + margin
            if widened_from < start_dt.date() - 2 * margin or widened_to > end_dt.date() + 2 * margin:
                leaves = self._l10n_in_search_sandwich_leaves(in_versions.employee_id, widened_from, widened_to)
        leaves = leaves.filtered(
            lambda leave: leave.company_id.country_id.code == 'IN' and leave._l10n_in_is_full_day_request()
        )
        if not leaves:
            return result

        leaves_per_employee_dict = leaves.grouped('employee_id')
        leaves_dates_by_employee = {
            employee: {
                (leave.request_date_from + timedelta(days=offset)): leave
                for leave in employee_leaves
                for offset in range((leave.request_date_to - leave.request_date_from).days + 1)
            }
            for employee, employee_leaves in leaves_per_employee_dict.items()
        }
        public_holiday_dates_by_company = leaves._l10n_in_get_public_holiday_dates_by_company()
        span_data = leaves._l10n_in_compute_sandwich_spans(
            leaves_dates_by_employee,
            public_holiday_dates_by_company,
        )
        if not span_data:
            return result

        attendance_intervals_by_calendar = {
            calendar: calendar._attendance_intervals_batch(
                start_dt,
                end_dt,
                resources_per_tz=versions._get_resources_per_tz(),
            )
            for calendar, versions in in_versions.grouped('resource_calendar_id').items()
        }

        updatable_entries_by_version_date = defaultdict(lambda: defaultdict(list))
        occupied_dates_by_version = defaultdict(set)
        for work_entry_vals in result:
            version = work_entry_vals['version_id']
            if version not in in_versions:
                continue
            entry_date = work_entry_vals.get('date')
            if not entry_date and work_entry_vals.get('date_start'):
                entry_start = work_entry_vals['date_start']
                if not entry_start.tzinfo:
                    entry_start = entry_start.replace(tzinfo=UTC)
                entry_date = entry_start.astimezone(ZoneInfo(version._get_tz())).date()
            if not entry_date:
                continue

            occupied_dates_by_version[version].add(entry_date)
            if not work_entry_vals.get('leave_ids'):
                updatable_entries_by_version_date[version][entry_date].append(work_entry_vals)

        for version in in_versions:
            employee = version.employee_id
            tz = ZoneInfo(version._get_tz())
            start_date = start_dt.astimezone(tz).date()
            end_date = end_dt.astimezone(tz).date()
            attendance_intervals = attendance_intervals_by_calendar.get(version.resource_calendar_id, {}).get(employee.resource_id.id, [])
            attendance_dates = {interval[0].astimezone(tz).date() for interval in attendance_intervals}
            occupied_dates = occupied_dates_by_version[version]
            updatable_entries_by_date = updatable_entries_by_version_date[version]
            employee_leaves = leaves_per_employee_dict.get(employee, self.env['hr.leave'])
            sandwich_dates = {}

            for leave in employee_leaves.sorted('id'):
                span_info = span_data.get(leave.id)
                if not span_info or not span_info.get('has_non_working'):
                    continue

                leave_start_date = max(span_info['start'], start_date)
                leave_end_date = min(span_info['end'], end_date)
                if leave_end_date < leave_start_date:
                    continue

                # Same public holidays as the span computation, so that the policy is applied
                # consistently with the leave duration.
                leave_public_holiday_dates = leave._l10n_in_get_leave_public_holiday_dates(public_holiday_dates_by_company)
                for offset in range((leave_end_date - leave_start_date).days + 1):
                    span_date = leave_start_date + timedelta(days=offset)
                    if not leave._l10n_in_is_counted_by_sandwich_policy(span_date, leave_public_holiday_dates):
                        continue

                    # Resolve overlapping spans consistently by leave creation order.
                    sandwich_dates.setdefault(span_date, leave)

            for span_date, leave in sandwich_dates.items():
                is_non_working_sandwich = (
                    span_date in public_holiday_dates_by_company.get(leave.company_id, {})
                    or span_date not in attendance_dates
                )
                if updatable_entries := updatable_entries_by_date.pop(span_date, []):
                    for work_entry_vals in updatable_entries:
                        work_entry_vals.update({
                            'work_entry_type_id': leave.work_entry_type_id,
                            'leave_ids': leave,
                            'l10n_in_is_sandwich_non_working': is_non_working_sandwich,
                        })
                    continue

                if span_date in attendance_dates or span_date in occupied_dates:
                    continue

                result.append({
                    'date': span_date,
                    'duration': version.resource_calendar_id.hours_per_day,
                    'work_entry_type_id': leave.work_entry_type_id,
                    'employee_id': employee,
                    'company_id': version.company_id,
                    'version_id': version,
                    'leave_ids': leave,
                    'l10n_in_is_sandwich_non_working': is_non_working_sandwich,
                })
                occupied_dates.add(span_date)
        return result
