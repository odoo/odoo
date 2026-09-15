from datetime import UTC

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrLeave(models.Model):
    _inherit = "hr.leave"

    l10n_fr_date_to_changed = fields.Boolean(export_string_translation=False)

    def _l10n_fr_leave_applies(self):
        # The french l10n is meant to be computed only in very specific cases:
        # - there is only one employee affected by the leave
        # - the company is french
        # - the leave_type is the reference leave_type of that company
        self.check_singleton()
        if _debug.logic.enabled:
            # the three cheap conditions only: the fourth calls
            # `_get_fr_reference_leave_type`, which RAISES when the company has
            # not set one, and an argument is evaluated before the level check
            _debug.logic(
                "fr_leave_gate",
                leave=self,
                employee=self.employee_id,
                country=self.company_id.country_id.code,
                own_calendar=(
                    self.resource_calendar_id != self.company_id.resource_calendar_id
                ),
            )
        return (
            self.employee_id
            and self.company_id.country_id.code == "FR"
            and self.resource_calendar_id != self.company_id.resource_calendar_id
            and self.holiday_status_id == self.company_id._get_fr_reference_leave_type()
        )

    def _get_fr_date_from_to(self, date_from, date_to):
        self.check_singleton()
        # What we need to compute is how much we will need to push date_to in order to account for the lost days
        # This gets even more complicated in two_weeks_calendars

        # The following computation doesn't work for resource calendars in
        # which the employee works zero hours.
        if not (self.resource_calendar_id.attendance_ids):
            _debug.logic(
                "fr_leave_refused",
                reason="calendar_has_no_attendance",
                leave=self,
                calendar=self.resource_calendar_id,
            )
            raise UserError(
                _(
                    "An employee can't take paid time off in a period without any work hours."
                )
            )

        if not self.request_unit_hours:
            # Use company's working schedule hours for the leave to avoid duration calculation issues.
            def adjust_date_range(
                date_from, date_to, from_period, to_period, attendance_ids, employee_id
            ):
                period_ids_from = attendance_ids.filtered(
                    lambda a: (
                        a.day_period in from_period
                        and int(a.dayofweek) == date_from.weekday()
                        and (
                            not a.two_weeks_calendar
                            or int(a.week_type) == a.get_week_type(date_from)
                        )
                    )
                )
                period_ids_to = attendance_ids.filtered(
                    lambda a: (
                        a.day_period in to_period
                        and int(a.dayofweek) == date_to.weekday()
                        and (
                            not a.two_weeks_calendar
                            or int(a.week_type) == a.get_week_type(date_to)
                        )
                    )
                )
                if period_ids_from:
                    min_hour = min(
                        attendance.hour_from for attendance in period_ids_from
                    )
                    date_from = self._to_utc(date_from, min_hour, employee_id)
                if period_ids_to:
                    max_hour = max(attendance.hour_to for attendance in period_ids_to)
                    date_to = self._to_utc(date_to, max_hour, employee_id)
                return date_from, date_to

            if self.request_unit_half:
                from_period = (
                    ["morning"]
                    if self.request_date_from_period == "am"
                    else ["afternoon"]
                )
                to_period = (
                    ["morning"]
                    if self.request_date_to_period == "am"
                    else ["afternoon"]
                )
            else:
                from_period = ["morning", "afternoon"]
                to_period = ["morning", "afternoon"]
            attendance_ids = (
                self.company_id.resource_calendar_id.attendance_ids
                | self.resource_calendar_id.attendance_ids
            )
            date_from, date_to = adjust_date_range(
                date_from,
                date_to,
                from_period,
                to_period,
                attendance_ids,
                self.employee_id,
            )

        similar = (
            date_from.date() == date_to.date()
            and self.request_date_from_period == self.request_date_to_period
        )
        if self.request_unit_half and similar and self.request_date_from_period == "am":
            # In normal workflows request_unit_half implies that date_from and date_to are the same
            # request_unit_half allows us to choose between `am` and `pm`
            # In a case where we work from mon-wed and request a half day in the morning
            # we do not want to push date_to since the next work attendance is actually in the afternoon
            date_from_weektype = str(
                self.env["resource.calendar.attendance"].get_week_type(date_from)
            )
            date_from_dayofweek = str(date_from.weekday())
            # Fetch the attendances we care about
            attendance_ids = self.resource_calendar_id.attendance_ids.filtered(
                lambda a: (
                    a.dayofweek == date_from_dayofweek
                    and a.day_period != "lunch"
                    and (
                        not self.resource_calendar_id.two_weeks_calendar
                        or a.week_type == date_from_weektype
                    )
                )
            )
            if len(attendance_ids) == 2:
                # The employee took the morning off on a day where he works the afternoon aswell
                _debug.logic(
                    "fr_leave_dates_unchanged",
                    reason="half_day_morning_on_a_full_working_day",
                    leave=self,
                    date_from=date_from,
                    date_to=date_to,
                )
                return (date_from, date_to)

        # Check calendars for working days until we find the right target, start at date_to + 1 day
        # Postpone date_target until the next working day
        date_start = date_from
        date_target = date_to
        # It is necessary to move the start date up to the first work day of
        # the employee calendar as otherwise days worked on by the company
        # calendar before the actual start of the leave would be taken into
        # account.
        while not self.resource_calendar_id._works_on_date(date_start):
            date_start += relativedelta(days=1)
        while not self.resource_calendar_id._works_on_date(
            date_target + relativedelta(days=1)
        ):
            date_target += relativedelta(days=1)

        # Undo the last day increment
        _debug.logic(
            "fr_leave_dates_extended",
            leave=self,
            requested_from=date_from,
            requested_to=date_to,
            legal_from=date_start,
            legal_to=date_target,
        )
        return (date_start, date_target)

    @api.depends(
        "request_date_from_period",
        "request_date_to_period",
        "request_hour_from",
        "request_hour_to",
        "request_date_from",
        "request_date_to",
        "request_unit_half",
        "request_unit_hours",
        "employee_id",
    )
    def _compute_date_from_to(self):
        super()._compute_date_from_to()
        for leave in self:
            if leave._l10n_fr_leave_applies():
                new_date_from, new_date_to = leave._get_fr_date_from_to(
                    leave.date_from, leave.date_to
                )
                _debug.lifecycle(
                    "fr_leave_dates_recomputed",
                    leave=leave,
                    was_from=leave.date_from,
                    now_from=new_date_from,
                    was_to=leave.date_to,
                    now_to=new_date_to,
                    pushed=new_date_to != leave.date_to,
                )
                if new_date_from != leave.date_from:
                    leave.date_from = new_date_from
                if new_date_to != leave.date_to:
                    leave.date_to = new_date_to
                    leave.l10n_fr_date_to_changed = True
                else:
                    leave.l10n_fr_date_to_changed = False

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        """
        In french time off laws, if an employee has a part time contract, when taking time off
        before one of his off day (compared to the company's calendar) it should also count the time
        between the time off and the next calendar work day/company off day (weekends).

        For example take an employee working mon-wed in a company where the regular calendar is mon-fri.
        If the employee were to take a time off ending on wednesday, the legal duration would count until friday.
        """
        if not resource_calendar:
            fr_leaves = self.filtered(lambda leave: leave._l10n_fr_leave_applies())
            duration_by_leave_id = super(HrLeave, self - fr_leaves)._get_durations(
                resource_calendar=resource_calendar
            )
            fr_leaves_by_company = fr_leaves.grouped("company_id")
            _debug.pipeline(
                "fr_durations_start",
                leaves=self,
                french=fr_leaves,
                companies=len(fr_leaves_by_company),
            )
            if fr_leaves:
                leaves = self.env["resource.schedule.exception"]
                public_holidays = leaves.search(
                    leaves._get_domain_public_holidays(
                        min(fr_leaves.mapped("date_from")) - relativedelta(days=1),
                        max(fr_leaves.mapped("date_to")) + relativedelta(days=1),
                        companies=fr_leaves.company_id,
                    )
                )
            for company, leaves in fr_leaves_by_company.items():
                company_cal = company.resource_calendar_id
                holidays_days_list = []
                public_holidays_filtered = public_holidays.filtered_domain(
                    [
                        ("calendar_id", "in", [False, company_cal.id]),
                        ("company_id", "=", company.id),
                    ]
                )
                for holiday in public_holidays_filtered:
                    tz = timezone(holiday.write_uid.tz or "UTC")
                    current = (
                        holiday.date_from.replace(tzinfo=UTC).astimezone(tz).date()
                    )
                    holiday_date_to = (
                        holiday.date_to.replace(tzinfo=UTC).astimezone(tz).date()
                    )
                    while current <= holiday_date_to:
                        holidays_days_list.append(current)
                        current += relativedelta(days=1)
                _debug.perf.count(
                    "fr_public_holidays_expanded",
                    company=company,
                    leaves=leaves,
                    public_holidays=public_holidays_filtered,
                    holiday_days=len(holidays_days_list),
                )
                for leave in leaves:
                    if leave.request_unit_half:
                        _debug.logic(
                            "fr_duration_delegated",
                            reason="half_day_request",
                            leave=leave,
                            calendar=company_cal,
                        )
                        duration_by_leave_id.update(
                            leave._get_durations(resource_calendar=company_cal)
                        )
                        continue
                    # Extend the end date to next working day
                    date_start = leave.date_from
                    date_end = leave.date_to
                    while not leave.resource_calendar_id._works_on_date(date_start):
                        date_start += relativedelta(days=1)
                    extended_date_end = date_end
                    while not company_cal._works_on_date(
                        extended_date_end + relativedelta(days=1)
                    ):
                        extended_date_end += relativedelta(days=1)
                    # Count number of days in company calendar
                    current = date_start.date()
                    end_date = extended_date_end.date()
                    legal_days = 0.0
                    while current <= end_date:
                        if current in holidays_days_list:
                            current += relativedelta(days=1)
                            continue
                        if company_cal._works_on_date(current):
                            legal_days += 1.0
                        current += relativedelta(days=1)
                    _debug.perf.count(
                        "fr_duration_standard_recomputed",
                        leave=leave,
                        leaves_in_company=leaves,
                    )
                    standard_duration = super()._get_durations(
                        resource_calendar=resource_calendar
                    )
                    _, hours = standard_duration.get(leave.id, (0.0, 0.0))

                    _debug.logic(
                        "fr_duration_legal",
                        leave=leave,
                        company=company,
                        requested_to=date_end,
                        extended_to=extended_date_end,
                        legal_days=legal_days,
                        standard_days=standard_duration.get(leave.id, (0.0, 0.0))[0],
                        hours=hours,
                    )
                    duration_by_leave_id[leave.id] = (legal_days, hours)

            return duration_by_leave_id
        return super()._get_durations(resource_calendar=resource_calendar)
