from collections import defaultdict
from datetime import UTC, datetime
from functools import reduce

from odoo import api, models
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog
from odoo.libs.intervals import Intervals

_debug = DebugLog(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_employees_from_attendees(self, everybody=False):
        domain = Domain("company_id", "in", self.env.companies.ids) & Domain(
            "partner_id", "!=", False
        )
        if not everybody:
            domain &= Domain("partner_id", "in", self.ids)
        return dict(
            self.env["hr.employee"]
            .sudo()
            ._read_group(domain, groupby=["partner_id"], aggregates=["id:recordset"])
        )

    def _get_schedule(self, start_period, stop_period, everybody=False, merge=True):
        employees_by_partner = self._get_employees_from_attendees(everybody)
        if not employees_by_partner:
            _debug.logic("schedule_empty", partners=self, everybody=everybody)
            return {}
        interval_by_calendar = defaultdict()
        calendar_periods_by_employee = defaultdict(list)
        resources_by_calendar = defaultdict(lambda: self.env["resource.resource"])

        employees = sum(employees_by_partner.values(), start=self.env["hr.employee"])
        calendar_periods_by_employee = employees._get_calendar_periods(
            start_period, stop_period
        )
        for employee, calendar_periods in calendar_periods_by_employee.items():
            for _start, _stop, calendar in calendar_periods:
                calendar = calendar or self.env.company.resource_calendar_id
                resources_by_calendar[calendar] += employee.resource_id

        _debug.perf.count(
            "schedule_calendars",
            partners=self,
            employees=len(calendar_periods_by_employee),
            calendars=len(resources_by_calendar),
            merge=merge,
        )
        for calendar, resources in resources_by_calendar.items():
            work_intervals = calendar._work_intervals_batch(
                start_period, stop_period, resources=resources
            )
            del work_intervals[False]
            if merge:
                interval_by_calendar[calendar] = reduce(
                    Intervals.__and__, work_intervals.values()
                )
            else:
                interval_by_calendar[calendar] = work_intervals

        schedule_by_employee = defaultdict(list)
        for employee, calendar_periods in calendar_periods_by_employee.items():
            employee_interval = Intervals([])
            for start, stop, calendar in calendar_periods:
                calendar = calendar or self.env.company.resource_calendar_id
                interval = Intervals([(start, stop, self.env["resource.calendar"])])
                if merge:
                    calendar_interval = interval_by_calendar[calendar]
                else:
                    calendar_interval = interval_by_calendar[calendar][
                        employee.resource_id.id
                    ]
                employee_interval |= calendar_interval & interval
            schedule_by_employee[employee] = employee_interval

        schedules = defaultdict()
        for partner, employees in employees_by_partner.items():
            partner_schedule = Intervals([])
            for employee in employees:
                if schedule_by_employee[employee]:
                    partner_schedule |= schedule_by_employee[employee]
            schedules[partner] = partner_schedule
        return schedules

    @api.model
    def get_working_hours_for_all_attendees(
        self, attendee_ids, date_from, date_to, everybody=False
    ):

        start_period = datetime.fromisoformat(date_from).replace(
            hour=0, minute=0, second=0, tzinfo=UTC
        )
        stop_period = datetime.fromisoformat(date_to).replace(
            hour=23, minute=59, second=59, tzinfo=UTC
        )

        schedule_by_partner = (
            self.env["res.partner"]
            .browse(attendee_ids)
            ._get_schedule(start_period, stop_period, everybody)
        )
        if not schedule_by_partner:
            _debug.logic("working_hours_none", attendees=len(attendee_ids))
            return []
        return self._interval_to_business_hours(
            reduce(Intervals.__and__, schedule_by_partner.values())
        )

    def _interval_to_business_hours(self, working_intervals):
        return (
            [
                {
                    "daysOfWeek": [(interval[0].weekday() + 1) % 7],
                    "startTime": interval[0]
                    .astimezone(timezone(self.env.user.tz or "UTC"))
                    .strftime("%H:%M"),
                    "endTime": interval[1]
                    .astimezone(timezone(self.env.user.tz or "UTC"))
                    .strftime("%H:%M"),
                }
                for interval in working_intervals
            ]
            if working_intervals
            else [
                {
                    "daysOfWeek": [7],
                    "startTime": datetime.today().strftime("00:00"),
                    "endTime": datetime.today().strftime("00:00"),
                }
            ]
        )
