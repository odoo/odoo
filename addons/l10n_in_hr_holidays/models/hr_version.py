# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo import api, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    @api.model
    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        if vals.pop('_l10n_in_exceptional_day', False):
            return False
        return super()._generate_work_entries_postprocess_adapt_to_calendar(vals)

    def _get_version_work_entries_values(self, date_start, date_stop):
        result = super()._get_version_work_entries_values(date_start, date_stop)

        indian_version = self.filtered(lambda version: version.company_id.country_id.code == "IN")
        if not indian_version:
            return result

        start_dt = date_start.astimezone(UTC).replace(tzinfo=None) if date_start.tzinfo else date_start
        end_dt = date_stop.astimezone(UTC).replace(tzinfo=None) if date_stop.tzinfo else date_stop

        exceptional_days = self.env["hr.leave"]._get_exceptional_holidays(start_dt, end_dt)
        if not exceptional_days:
            return result

        grouped_leaves = self.env["hr.leave"]._read_group(
            domain=[
                ("employee_id", "in", indian_version.employee_id.ids),
                ("state", "=", "validate"),
                ("date_from", "<=", end_dt),
                ("date_to", ">=", start_dt),
            ],
            groupby=["employee_id"],
            aggregates=["id:recordset"],
        )
        leaves_per_employee = dict(grouped_leaves)

        for version in indian_version:
            tz = ZoneInfo(version._get_tz())
            exceptional_dates = set()
            compensatory_dates = set()

            for holiday in exceptional_days:
                holiday_start = holiday.date_from.replace(tzinfo=UTC).astimezone(tz).date()
                holiday_end = holiday.date_to.replace(tzinfo=UTC).astimezone(tz).date()

                exceptional_dates.update(
                    holiday_start + timedelta(days=i)
                    for i in range((holiday_end - holiday_start).days + 1)
                )
                if holiday.working_start_date and holiday.working_end_date:
                    comp_start = holiday.working_start_date.date()
                    comp_end = holiday.working_end_date.date()

                    compensatory_dates.update(
                        comp_start + timedelta(days=i)
                        for i in range((comp_end - comp_start).days + 1)
                    )

            version_exceptional_dates = {
                day
                for day in exceptional_dates
                if start_dt.date() <= day <= end_dt.date()
            }

            version_compensatory_dates = {
                day
                for day in compensatory_dates
                if start_dt.date() <= day <= end_dt.date()
            }

            if not version_exceptional_dates and not version_compensatory_dates:
                continue

            approved_leaves = leaves_per_employee.get(version.employee_id, self.env["hr.leave"])

            leave_type_by_date = {}
            for leave in approved_leaves:
                leave_start = leave.date_from.replace(tzinfo=UTC).astimezone(tz).date()
                leave_end = leave.date_to.replace(tzinfo=UTC).astimezone(tz).date()

                for day in version_exceptional_dates:
                    if leave_start <= day <= leave_end:
                        leave_type_by_date[day] = leave.work_entry_type_id

            leave_dates = set(leave_type_by_date.keys())
            attendance_dates = version_exceptional_dates - leave_dates

            result = [
                vals
                for vals in result
                if not (
                    vals["employee_id"] == version.employee_id
                    and (
                        vals["date_start"].replace(tzinfo=UTC).astimezone(tz).date()
                        in version_exceptional_dates
                        or (
                            vals["date_start"].replace(tzinfo=UTC).astimezone(tz).date()
                            in version_compensatory_dates
                            and vals["work_entry_type_id"].count_as == "working_time"
                        )
                    )
                )
            ]

            if attendance_dates:
                result += version._l10n_in_get_exceptional_day_attendance_vals(attendance_dates)
            if leave_dates:
                result += version._l10n_in_get_exceptional_day_leave_vals(leave_type_by_date)
        return result

    def _l10n_in_get_attendance_intervals_for_date(self, target_date):
        """Return the (hour_from, hour_to) blocks to use for ``target_date`` when
        converting it to/from an exceptional working day.

        Uses the calendar's fixed weekly attendance lines for that weekday when
        available (dayofweek '0' = Monday ... '6' = Sunday, same indexing as
        ``date.weekday()``). Falls back to a single block of ``hours_per_day``
        hours when the weekday has no scheduled hours at all (e.g. a public
        holiday falling on a weekly day off), so the day still counts as one
        full day in the payslip.
        """
        self.ensure_one()
        day_lines = self.resource_calendar_id.attendance_ids.filtered(
            lambda a: a.dayofweek == str(target_date.weekday()) and a.hour_to > a.hour_from
        )
        if day_lines:
            return [(line.hour_from, line.hour_to) for line in day_lines]
        return [(0, self._get_hours_per_day() or 8.0)]

    def _l10n_in_get_exceptional_day_leave_vals(self, leave_type_by_date):
        """Generate leave work entries for exceptional dates that are covered
        by an approved leave, using the same hour template as a normal
        working day but stamped with the leave's own work entry type.
        """
        self.ensure_one()

        vals_list = []
        for leave_date, work_entry_type in leave_type_by_date.items():
            if not work_entry_type:
                continue
            day_midnight = datetime.combine(leave_date, time.min, tzinfo=ZoneInfo(self._get_tz()))
            for hour_from, hour_to in self._l10n_in_get_attendance_intervals_for_date(leave_date):
                interval_start = day_midnight + timedelta(hours=hour_from)
                interval_stop = day_midnight + timedelta(hours=hour_to)
                vals_list.append({
                    'date_start': interval_start.astimezone(UTC).replace(tzinfo=None),
                    'date_stop': interval_stop.astimezone(UTC).replace(tzinfo=None),
                    'work_entry_type_id': work_entry_type,
                    'employee_id': self.employee_id,
                    'version_id': self,
                    'company_id': self.company_id,
                    # Leave work entry types are normally 'count_as': 'absence', which makes
                    # the base engine recompute the duration from the calendar's own weekly
                    # schedule instead of the interval above - and that recompute yields 0
                    # hours on a date the calendar doesn't normally work (e.g. a public
                    # holiday that fell on a weekly day off). This flag tells
                    # _generate_work_entries_postprocess_adapt_to_calendar to keep our
                    # explicit hour_from/hour_to instead.
                    '_l10n_in_exceptional_day': True,
                })
        return vals_list

    def _l10n_in_get_exceptional_day_attendance_vals(self, exceptional_dates):
        self.ensure_one()

        vals_list = []
        for exceptional_date in exceptional_dates:
            day_midnight = datetime.combine(exceptional_date, time.min, tzinfo=ZoneInfo(self._get_tz()))
            for hour_from, hour_to in self._l10n_in_get_attendance_intervals_for_date(exceptional_date):
                interval_start = day_midnight + timedelta(hours=hour_from)
                interval_stop = day_midnight + timedelta(hours=hour_to)
                vals_list.append({
                    'date_start': interval_start.astimezone(UTC).replace(tzinfo=None),
                    'date_stop': interval_stop.astimezone(UTC).replace(tzinfo=None),
                    'work_entry_type_id': self.env.ref('hr_work_entry.in_work_entry_type_attendance'),
                    'employee_id': self.employee_id,
                    'version_id': self,
                    'company_id': self.company_id,
                })
        return vals_list
