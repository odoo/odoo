from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from functools import partial
from typing import TYPE_CHECKING, Any, NamedTuple
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain
from odoo.libs.datetime import timezone
from odoo.libs.intervals import Intervals
from odoo.libs.numbers import float_round
from odoo.models import ValuesType
from odoo.tools import SQL, date_utils, float_compare
from odoo.tools.date_utils import float_to_time, localized, to_timezone

from .utils import HOURS_PER_DAY
from odoo.addons.base.models.res_partner import _selection_timezones

if TYPE_CHECKING:
    from .resource_calendar_attendance import ResourceCalendarAttendance
    from .resource_resource import ResourceResource


class DummyAttendance(NamedTuple):
    hour_from: float
    hour_to: float
    dayofweek: str
    day_period: str | None
    week_type: str | None


_PLAN_WINDOW = timedelta(days=14)
_PLAN_MAX_ITERATIONS = 100


class ResourceCalendar(models.Model):
    _name = "resource.calendar"
    _description = "Resource Working Time"

    name = fields.Char(required=True)
    active = fields.Boolean(
        default=True,
        help="If the active field is set to false, it will allow you to hide the Working Time without removing it.",
    )
    attendance_ids = fields.One2many(
        comodel_name="resource.calendar.attendance",
        inverse_name="calendar_id",
        string="Working Time",
        compute="_compute_attendance_ids",
        store=True,
        copy=True,
        readonly=False,
    )
    attendance_ids_1st_week = fields.One2many(
        comodel_name="resource.calendar.attendance",
        inverse_name="calendar_id",
        string="Working Time 1st Week",
        compute="_compute_two_weeks_attendance",
        inverse="_inverse_two_weeks_calendar",
    )
    attendance_ids_2nd_week = fields.One2many(
        comodel_name="resource.calendar.attendance",
        inverse_name="calendar_id",
        string="Working Time 2nd Week",
        compute="_compute_two_weeks_attendance",
        inverse="_inverse_two_weeks_calendar",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index="btree_not_null",
        domain=lambda self: [("id", "in", self.env.companies.ids)],
    )
    leave_ids = fields.One2many(
        comodel_name="resource.schedule.exception",
        inverse_name="calendar_id",
        string="Time Off",
    )
    resource_ids = fields.One2many(
        comodel_name="resource.resource",
        inverse_name="calendar_id",
        string="Work Resources",
    )
    schedule_type = fields.Selection(
        selection=[
            ("flexible", "Flexible"),
            ("fully_fixed", "Fully Fixed"),
        ],
        compute="_compute_schedule_type",
        inverse="_inverse_schedule_type",
        help="Choose which level of definition you want to define on your Schedule\n"
        "- Flexible : Define an amount of hours to work on the week.\n"
        "- Fully Fixed : define the days, periods and the start & end time for each period of the day",
    )
    duration_based = fields.Boolean(
        string="Attendance based on duration",
        help="The hours will be centered around 12:00 to cover the duration for the day",
    )
    flexible_hours = fields.Boolean(
        help="When enabled, it will allow employees to work flexibly, without relying on the company's working schedule (working hours)."
    )
    full_time_required_hours = fields.Float(
        string="Full Time Equivalent",
        compute="_compute_full_time_required_hours",
        store=True,
        readonly=False,
        help="Number of hours to work on the company schedule to be considered as fulltime.",
    )
    global_leave_ids = fields.One2many(
        comodel_name="resource.schedule.exception",
        inverse_name="calendar_id",
        string="Global Time Off",
        copy=True,
        domain=[("resource_id", "=", False)],
    )
    hours_per_day = fields.Float(
        string="Average Hour per Day",
        digits=(2, 2),
        compute="_compute_hours_per_day",
        store=True,
        readonly=False,
        help="Average hours per day a resource is supposed to work with this calendar.",
    )
    hours_per_week = fields.Float(
        string="Hours per Week",
        compute="_compute_hours_per_week",
        store=True,
        copy=False,
        readonly=False,
    )
    is_fulltime = fields.Boolean(
        string="Is Full Time",
        compute="_compute_work_time",
    )
    two_weeks_calendar = fields.Boolean(string="Calendar in 2 weeks mode")
    two_weeks_explanation = fields.Char(
        string="Explanation",
        compute="_compute_two_weeks_explanation",
    )

    tz = fields.Selection(
        selection=_selection_timezones,
        string="Timezone",
        default=lambda self: self._default_tz(),
        required=True,
        help="The time zone of this schedule's company-level uses: the company working hours, and the public holidays and closures entered on it. A resource working this schedule reads its hours in the resource's own time zone, so one 08:00-17:00 schedule means 08:00-17:00 local time for employees deployed in other zones.",
    )
    tz_offset = fields.Char(
        string="Timezone offset",
        compute="_compute_tz_offset",
    )
    work_resources_count = fields.Integer(
        string="Work Resources count",
        compute="_compute_work_resources_count",
    )
    work_time_rate = fields.Float(
        compute="_compute_work_time",
        search="_search_work_time_rate",
        help="Work time rate versus full time working schedule, should be between 0 and 100 %.",
    )

    @api.constrains("attendance_ids", "two_weeks_calendar")
    def _check_attendance_ids(self):
        for calendar in self:
            lines = calendar.attendance_ids.filtered(
                lambda attendance: not attendance.display_type
            )
            if not calendar.two_weeks_calendar:
                calendar._check_overlap(lines)
                continue
            sections = calendar.attendance_ids - lines
            if (
                sections
                and not calendar.attendance_ids.sorted("sequence")[0].display_type
            ):
                raise ValidationError(
                    self.env._(
                        "In a calendar with 2 weeks mode, all periods need to be in the sections."
                    )
                )
            if orphans := lines.filtered(lambda attendance: not attendance.week_type):
                raise ValidationError(
                    self.env._(
                        "%(names)s: a line on a 2 weeks calendar must belong"
                        " to the first or the second week.",
                        names=", ".join(orphans.mapped("name")),
                    )
                )
            for week_lines in lines.grouped("week_type").values():
                calendar._check_overlap(week_lines)

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        res = super().default_get(fields)
        if not res.get("name") and res.get("company_id"):
            res["name"] = self.env._(
                "Working Hours of %s",
                self.env["res.company"].browse(res["company_id"]).name,
            )
        company = self.env["res.company"].browse(
            res.get("company_id", self.env.company.id)
        )
        if "attendance_ids" in fields and not res.get("attendance_ids"):
            res["attendance_ids"] = self._get_default_attendance_ids(company)
            res["two_weeks_calendar"] = company.resource_calendar_id.two_weeks_calendar
        if "full_time_required_hours" in fields and not res.get(
            "full_time_required_hours"
        ):
            res["full_time_required_hours"] = (
                company.resource_calendar_id.full_time_required_hours
            )
        return res

    def _default_tz(self):
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        return (
            self.env.context.get("tz")
            or self.env.user.tz
            or (admin and admin.tz)
            or "UTC"
        )

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        new_lines = "attendance_ids" in (default or {})
        for calendar, vals in zip(self, vals_list, strict=True):
            vals["name"] = self.env._("%s (copy)", calendar.name)
            if calendar.flexible_hours:
                vals.setdefault("hours_per_week", calendar.hours_per_week)
            elif new_lines and "hours_per_day" not in default:
                vals.pop("hours_per_day", None)
        return vals_list

    @api.depends("two_weeks_calendar", "attendance_ids.week_type")
    def _compute_two_weeks_attendance(self):
        for calendar in self:
            if not calendar.two_weeks_calendar:
                calendar.attendance_ids_1st_week = False
                calendar.attendance_ids_2nd_week = False
                continue
            calendar.attendance_ids_1st_week = calendar.attendance_ids.filtered(
                lambda a: a.week_type == "0"
            )
            calendar.attendance_ids_2nd_week = calendar.attendance_ids.filtered(
                lambda a: a.week_type == "1"
            )

    @api.depends("hours_per_week", "company_id.resource_calendar_id.hours_per_week")
    def _compute_full_time_required_hours(self):
        for calendar in self.filtered("company_id"):
            calendar.full_time_required_hours = (
                calendar.company_id.resource_calendar_id.hours_per_week
            )

    @api.depends("flexible_hours")
    def _compute_schedule_type(self):
        for calendar in self:
            calendar.schedule_type = (
                "flexible" if calendar.flexible_hours else "fully_fixed"
            )

    @api.depends("company_id")
    def _compute_attendance_ids(self):
        for calendar in self.filtered(
            lambda c: (
                not c._origin or (c._origin.company_id != c.company_id and c.company_id)
            )
        ):
            company_calendar = calendar.company_id.resource_calendar_id
            calendar.update(
                {
                    "two_weeks_calendar": company_calendar.two_weeks_calendar,
                    "tz": company_calendar.tz,
                    "attendance_ids": [Command.clear()]
                    + [
                        Command.create(attendance._copy_attendance_vals())
                        for attendance in company_calendar.attendance_ids
                    ],
                }
            )

    @api.depends(
        "attendance_ids",
        "attendance_ids.hour_from",
        "attendance_ids.hour_to",
        "attendance_ids.duration_hours",
        "attendance_ids.day_period",
        "attendance_ids.display_type",
        "duration_based",
        "two_weeks_calendar",
        "flexible_hours",
    )
    def _compute_hours_per_day(self):
        for calendar in self.filtered(lambda c: not c.flexible_hours):
            calendar.hours_per_day = float_round(
                calendar._get_hours_per_day(), precision_digits=2
            )

    @api.depends(
        "attendance_ids",
        "attendance_ids.hour_from",
        "attendance_ids.hour_to",
        "attendance_ids.duration_hours",
        "attendance_ids.day_period",
        "attendance_ids.display_type",
        "duration_based",
        "two_weeks_calendar",
        "flexible_hours",
    )
    def _compute_hours_per_week(self):
        for calendar in self.filtered(lambda c: not c.flexible_hours):
            calendar.hours_per_week = float_round(
                calendar._get_hours_per_week(), precision_digits=2
            )

    def _compute_two_weeks_explanation(self):
        today = fields.Date.context_today(self)
        week_type = self.env["resource.calendar.attendance"].get_week_type(today)
        week_type_str = (
            self.env._("the second") if week_type else self.env._("the first")
        )
        first_day = date_utils.start_of(today, "week")
        last_day = date_utils.end_of(today, "week")
        explanation = self.env._(
            "The current week (from %(first_day)s to %(last_day)s) is %(number)s week.",
            first_day=first_day,
            last_day=last_day,
            number=week_type_str,
        )
        for calendar in self:
            calendar.two_weeks_explanation = explanation

    @api.depends("tz")
    def _compute_tz_offset(self):
        for calendar in self:
            calendar.tz_offset = datetime.now(timezone(calendar.tz or "GMT")).strftime(
                "%z"
            )

    @api.depends("resource_ids")
    def _compute_work_resources_count(self):
        resources_per_calendar = dict(
            self.env["resource.resource"]._read_group(
                domain=[("calendar_id", "in", self.ids)],
                groupby=["calendar_id"],
                aggregates=["__count"],
            )
        )
        for calendar in self:
            calendar.work_resources_count = resources_per_calendar.get(calendar, 0)

    @api.depends("hours_per_week", "full_time_required_hours")
    def _compute_work_time(self):
        for calendar in self:
            if calendar.full_time_required_hours:
                calendar.work_time_rate = (
                    calendar.hours_per_week / calendar.full_time_required_hours * 100
                )
            else:
                calendar.work_time_rate = 100

            calendar.is_fulltime = (
                float_compare(
                    calendar.full_time_required_hours, calendar.hours_per_week, 3
                )
                == 0
            )

    _WORK_TIME_RATE_SQL = SQL(
        "CASE WHEN COALESCE(full_time_required_hours, 0) > 0"
        " THEN hours_per_week / full_time_required_hours * 100"
        " ELSE 100 END"
    )

    def _inverse_two_weeks_calendar(self):
        for calendar in self:
            if not calendar.two_weeks_calendar:
                continue
            calendar.attendance_ids = (
                calendar.attendance_ids_1st_week + calendar.attendance_ids_2nd_week
            )

    def _inverse_schedule_type(self):
        for calendar in self:
            calendar.flexible_hours = calendar.schedule_type == "flexible"

    @api.model
    def _search_work_time_rate(self, operator, value):
        scalar_ops = {op: SQL(op) for op in ("<", ">", "<=", ">=", "=", "!=")}
        rate = self._WORK_TIME_RATE_SQL
        if operator in scalar_ops:
            if not isinstance(value, int | float):
                return NotImplemented
            condition = SQL("%s %s %s", rate, scalar_ops[operator], value)
        elif operator in ("in", "not in"):
            if not all(isinstance(v, int | float) for v in value):
                return NotImplemented
            values = list(value)
            condition = (
                SQL("%s = ANY(%s)", rate, values)
                if operator == "in"
                else SQL("%s != ALL(%s)", rate, values)
            )
        else:
            return NotImplemented

        self.flush_model(["hours_per_week", "full_time_required_hours"])
        self.env.cr.execute(SQL("SELECT id FROM resource_calendar WHERE %s", condition))
        return [("id", "in", [row[0] for row in self.env.cr.fetchall()])]

    @api.onchange("attendance_ids")
    def _onchange_attendance_ids(self):
        if not self.two_weeks_calendar:
            return

        even_week_seq = self.attendance_ids.filtered(
            lambda att: att.display_type == "line_section" and att.week_type == "0"
        )
        odd_week_seq = self.attendance_ids.filtered(
            lambda att: att.display_type == "line_section" and att.week_type == "1"
        )
        if len(even_week_seq) != 1 or len(odd_week_seq) != 1:
            raise ValidationError(self.env._("You can't delete section between weeks."))

        even_week_seq = even_week_seq.sequence
        odd_week_seq = odd_week_seq.sequence

        for line in self.attendance_ids.filtered(lambda att: att.display_type is False):
            if even_week_seq > odd_week_seq:
                line.week_type = "1" if even_week_seq > line.sequence else "0"
            else:
                line.week_type = "0" if odd_week_seq > line.sequence else "1"

    def switch_calendar_type(self):
        self.check_singleton()
        if not self.two_weeks_calendar:
            self.write(
                {
                    "two_weeks_calendar": True,
                    "attendance_ids": [Command.clear()]
                    + self._get_two_weeks_attendance(),
                }
            )
        else:
            self.write(
                {
                    "two_weeks_calendar": False,
                    "duration_based": False,
                    "attendance_ids": [Command.clear()]
                    + [
                        Command.create(vals)
                        for vals in self._single_week_attendance_vals(
                            self._prepare_default_attendance_vals(self.company_id)
                        )
                    ],
                }
            )

    def switch_based_on_duration(self):
        self.check_singleton()
        self.duration_based = not self.duration_based
        if self.duration_based:
            self.attendance_ids.filtered(lambda att: att.day_period == "lunch").unlink()
            return
        default_vals = self._single_week_attendance_vals(
            self._prepare_default_attendance_vals(self.company_id)
        )
        if self.two_weeks_calendar:
            commands = self._get_two_weeks_attendance(default_vals)
        else:
            commands = [Command.create(vals) for vals in default_vals]
        self.attendance_ids = [Command.clear()] + commands

    def _prepare_dummy_attendance(self, hours, days):
        return self.env["resource.calendar.attendance"].new(
            {"duration_hours": hours, "duration_days": days}
        )

    def _fully_flexible_attendance_intervals(self, start_datetime, end_datetime, tz):
        self.check_singleton()
        expected_day_hours = self.hours_per_day or HOURS_PER_DAY
        intervals = []
        day = start_datetime.date()
        last_day = (end_datetime - timedelta(microseconds=1)).date()
        while day <= last_day:
            midnight = datetime.combine(day, time.min).replace(tzinfo=tz)
            next_midnight = datetime.combine(day + timedelta(days=1), time.min).replace(
                tzinfo=tz
            )
            day_start = max(start_datetime, midnight)
            day_end = min(end_datetime, next_midnight)
            if day_end > day_start:
                covered_hours = (day_end - day_start).total_seconds() / 3600
                intervals.append(
                    (
                        day_start,
                        day_end,
                        self._prepare_dummy_attendance(
                            covered_hours,
                            min(1.0, covered_hours / expected_day_hours),
                        ),
                    )
                )
            day += timedelta(days=1)
        return intervals

    @staticmethod
    def _center_block_on_noon(day, hours, tz, lower, upper):
        midpoint = datetime.combine(day, time(12, 0)).replace(tzinfo=tz)
        start_time = midpoint - timedelta(hours=hours / 2)
        end_time = midpoint + timedelta(hours=hours / 2)
        if start_time < lower:
            start_time = lower
            end_time = start_time + timedelta(hours=hours)
        elif end_time > upper:
            end_time = upper
            start_time = end_time - timedelta(hours=hours)
        return start_time, end_time

    def _get_flexible_hours_per_week(self):
        self.check_singleton()
        return self.hours_per_week or self.full_time_required_hours

    def _flexible_attendance_intervals(self, start_datetime, end_datetime, tz):
        self.check_singleton()
        max_hours_per_week = self._get_flexible_hours_per_week()
        max_hours_per_day = self.hours_per_day or HOURS_PER_DAY
        first_day = start_datetime.date()
        last_day = (end_datetime - timedelta(microseconds=1)).date()
        total_hours = (end_datetime - start_datetime).total_seconds() / 3600
        intervals = []
        chunk_start = first_day
        while chunk_start <= last_day:
            chunk_end = min(chunk_start + timedelta(days=6), last_day)
            remaining_hours = min(max_hours_per_week, total_hours)

            day = chunk_start
            while day <= chunk_end:
                if remaining_hours <= 0:
                    break
                day_start = datetime.combine(day, time.min).replace(tzinfo=tz)
                day_end = datetime.combine(day, time.max).replace(tzinfo=tz)
                day_period_start = max(start_datetime, day_start)
                day_period_end = min(end_datetime, day_end)
                allocate_hours = min(
                    max_hours_per_day,
                    remaining_hours,
                    (day_period_end - day_period_start).total_seconds() / 3600,
                )
                remaining_hours -= allocate_hours
                start_time, end_time = self._center_block_on_noon(
                    day,
                    allocate_hours,
                    tz,
                    day_period_start,
                    day_period_end,
                )
                intervals.append(
                    (
                        start_time,
                        end_time,
                        self._prepare_dummy_attendance(
                            allocate_hours,
                            min(1.0, allocate_hours / max_hours_per_day),
                        ),
                    )
                )
                day += timedelta(days=1)
            chunk_start += timedelta(days=7)
        return intervals

    def _attendance_intervals_batch(
        self,
        start_dt: datetime,
        end_dt: datetime,
        resources: ResourceResource | None = None,
        domain: list | None = None,
        tz: ZoneInfo | str | None = None,
        lunch: bool = False,
    ) -> dict[int | bool, Intervals]:
        if not (start_dt.tzinfo and end_dt.tzinfo):
            raise ValueError("start_dt and end_dt must be timezone-aware")
        if not self:
            raise ValueError(
                "_attendance_intervals_batch requires a calendar; a resource"
                " without one is fully flexible and has no attendance lines"
            )
        self.check_singleton()
        if isinstance(tz, str):
            tz = timezone(tz)
        if not resources:
            resources = self.env["resource.resource"]
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env["resource.resource"]]

        if not resources and self.flexible_hours and lunch:
            # No per-resource calendar to disagree with self here.
            return {False: Intervals([], keep_distinct=True)}

        domain = Domain.AND(
            [
                Domain(domain or Domain.TRUE),
                Domain("calendar_id", "=", self.id),
                Domain("display_type", "=", False),
                Domain("day_period", "!=" if not lunch else "=", "lunch"),
            ]
        )

        calendar_attendances = self.env["resource.calendar.attendance"].search_fetch(
            domain,
            ["dayofweek", "week_type", "hour_from", "hour_to"],
        )
        resources_per_tz = defaultdict(list)
        for resource in resources_list:
            resources_per_tz[tz or timezone((resource or self).tz)].append(resource)
        attendances_per_day = [
            self.env["resource.calendar.attendance"] for _ in range(14)
        ]
        weekdays = set()
        for attendance in calendar_attendances:
            weekday = int(attendance.dayofweek)
            weekdays.add(weekday)
            if self.two_weeks_calendar:
                weektype = int(attendance.week_type)
                attendances_per_day[weekday + 7 * weektype] |= attendance
            else:
                attendances_per_day[weekday] |= attendance
                attendances_per_day[weekday + 7] |= attendance

        start = start_dt.astimezone(UTC)
        end = end_dt.astimezone(UTC)
        bounds_per_tz = {
            tz: (start_dt.astimezone(tz), end_dt.astimezone(tz))
            for tz in resources_per_tz
        }
        for low, high in bounds_per_tz.values():
            start = min(start, low.replace(tzinfo=UTC))
            end = max(end, high.replace(tzinfo=UTC))
        days = rrule(DAILY, start.date(), until=end.date(), byweekday=weekdays)
        ResourceCalendarAttendance = self.env["resource.calendar.attendance"]
        base_result = []
        for day in days:
            week_type = ResourceCalendarAttendance.get_week_type(day)
            attendances = attendances_per_day[day.weekday() + 7 * week_type]
            for attendance in attendances:
                day_from = datetime.combine(day, float_to_time(attendance.hour_from))
                day_to = datetime.combine(day, float_to_time(attendance.hour_to))
                base_result.append((day_from, day_to, attendance))

        result_per_tz = {
            tz: [
                (
                    max(bounds_per_tz[tz][0], val[0].replace(tzinfo=tz)),
                    min(bounds_per_tz[tz][1], val[1].replace(tzinfo=tz)),
                    val[2],
                )
                for val in base_result
            ]
            for tz in resources_per_tz
        }
        resource_calendars = resources._get_calendar_at(start_dt, tz)
        result_per_resource_id = {}
        for tz, tz_resources in resources_per_tz.items():
            res = result_per_tz[tz]

            res_intervals = Intervals(res, keep_distinct=True)
            start_datetime = start_dt.astimezone(tz)
            end_datetime = end_dt.astimezone(tz)

            for resource in tz_resources:
                result_per_resource_id[resource.id] = (
                    self._resource_attendance_intervals(
                        resource,
                        resource_calendars,
                        res_intervals,
                        start_datetime,
                        end_datetime,
                        tz,
                        lunch,
                    )
                )
        return result_per_resource_id

    def _resource_attendance_intervals(
        self,
        resource: ResourceResource,
        resource_calendars: dict,
        fixed_intervals: Intervals,
        start_datetime: datetime,
        end_datetime: datetime,
        tz: ZoneInfo,
        lunch: bool,
    ) -> Intervals:
        if resource and not resource_calendars.get(resource):
            return Intervals(
                self._fully_flexible_attendance_intervals(
                    start_datetime, end_datetime, tz
                ),
                keep_distinct=True,
            )
        calendar = resource_calendars[resource] if resource else self
        if not calendar.flexible_hours:
            return fixed_intervals
        if lunch:
            return Intervals([], keep_distinct=True)
        return Intervals(
            calendar._flexible_attendance_intervals(start_datetime, end_datetime, tz),
            keep_distinct=True,
        )

    def _handle_flexible_leave_interval(
        self, dt0: datetime, dt1: datetime, leave: Any
    ) -> tuple[datetime, datetime]:
        if dt1 <= dt0:
            return dt0, dt1
        tz = dt0.tzinfo
        last_day = (dt1 - timedelta(microseconds=1)).date()
        dt0 = datetime.combine(dt0.date(), time.min).replace(tzinfo=tz)
        dt1 = datetime.combine(last_day, time.max).replace(tzinfo=tz)
        return dt0, dt1

    def _with_default_leave_type(self, domain: list | None) -> list:
        # The kernel's one question of a kind of time: does it come out of the
        # working schedule. A caller naming the kind itself is left alone.
        leave_only = Domain("time_type_id.is_work", "=", False)
        if domain is None:
            return list(leave_only)
        given = Domain(domain)
        if any(
            condition.field_expr.startswith("time_type_id")
            for condition in given.iter_conditions()
        ):
            return list(given)
        return list(given & leave_only)

    def _leave_intervals(
        self,
        start_dt: datetime,
        end_dt: datetime,
        resource: ResourceResource | None = None,
        domain: list | None = None,
        tz: ZoneInfo | str | None = None,
    ) -> Intervals:
        if resource is None:
            resource = self.env["resource.resource"]
        return self._leave_intervals_batch(
            start_dt,
            end_dt,
            resources=resource,
            domain=domain,
            tz=tz,
        )[resource.id]

    def _leave_intervals_batch(
        self,
        start_dt: datetime,
        end_dt: datetime,
        resources: ResourceResource | None = None,
        domain: list | None = None,
        tz: ZoneInfo | str | None = None,
    ) -> dict[int | bool, Intervals]:
        if not (start_dt.tzinfo and end_dt.tzinfo):
            raise ValueError("start_dt and end_dt must be timezone-aware")

        if isinstance(tz, str):
            tz = timezone(tz)

        domain = self._with_default_leave_type(domain)

        resources_list = list(resources) if resources else []

        resources_list.append(self.env["resource.resource"])
        calendar_leaf = (
            ("calendar_id", "in", [False] + self.ids)
            if self
            else ("calendar_id", "=", False)
        )
        domain = [
            *domain,
            calendar_leaf,
            ("resource_id", "in", [False] + [r.id for r in resources_list]),
            ("date_from", "<=", end_dt.astimezone(UTC).replace(tzinfo=None)),
            ("date_to", ">=", start_dt.astimezone(UTC).replace(tzinfo=None)),
        ]

        window_per_resource = [
            (
                resource,
                resource_tz := tz or timezone((resource or self).tz or "UTC"),
                start_dt.astimezone(resource_tz),
                end_dt.astimezone(resource_tz),
            )
            for resource in resources_list
        ]

        result = defaultdict(list)
        leave_bounds = {}
        all_leaves = self.env["resource.schedule.exception"].search(domain)
        for leave in all_leaves:
            leave_resource = leave.resource_id
            leave_company = leave.company_id
            leave_date_from = leave.date_from
            leave_date_to = leave.date_to
            for resource, resource_tz, start, end in window_per_resource:
                if leave_resource.id not in [False, resource.id]:
                    continue
                if (
                    not leave_resource
                    and resource
                    and leave_company
                    and resource.company_id
                    and resource.company_id != leave_company
                ):
                    continue
                bounds_key = (leave.id, resource_tz)
                if bounds_key in leave_bounds:
                    dt0, dt1 = leave_bounds[bounds_key]
                else:
                    dt0 = leave_date_from.astimezone(resource_tz)
                    dt1 = leave_date_to.astimezone(resource_tz)
                    if leave_resource and leave_resource._is_flexible():
                        dt0, dt1 = self._handle_flexible_leave_interval(dt0, dt1, leave)
                    leave_bounds[bounds_key] = (dt0, dt1)
                result[resource.id].append((max(start, dt0), min(end, dt1), leave))

        return {r.id: Intervals(result[r.id]) for r in resources_list}

    def _work_intervals_batch(
        self,
        start_dt: datetime,
        end_dt: datetime,
        resources: ResourceResource | None = None,
        domain: list | None = None,
        tz: ZoneInfo | str | None = None,
        compute_leaves: bool = True,
    ) -> dict[int | bool, Intervals]:
        if not resources:
            resources = self.env["resource.resource"]
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env["resource.resource"]]

        effective_tz = tz or self.env.context.get("employee_timezone")
        attendance_intervals = self._attendance_intervals_batch(
            start_dt,
            end_dt,
            resources,
            tz=effective_tz,
        )
        if compute_leaves:
            leave_intervals = self._leave_intervals_batch(
                start_dt, end_dt, resources, domain, tz=effective_tz
            )
            blocked_intervals = self._hard_reservation_intervals_batch(
                start_dt, end_dt, resources
            )
            return {
                r.id: (
                    attendance_intervals[r.id]
                    - leave_intervals[r.id]
                    - blocked_intervals[r.id]
                )
                for r in resources_list
            }
        return {r.id: attendance_intervals[r.id] for r in resources_list}

    def _hard_reservation_intervals_batch(
        self,
        start_dt: datetime,
        end_dt: datetime,
        resources: ResourceResource | None = None,
    ) -> dict[int | bool, Intervals]:
        empty = self.env["resource.resource"]
        result: dict[int | bool, Intervals] = {empty.id: Intervals()}
        if not resources:
            return result
        if self.env.context.get("resource_capacity_aware"):
            return result | {resource.id: Intervals() for resource in resources}
        booked = self.env["resource.reservation"]._reservation_intervals_batch(
            start_dt,
            end_dt,
            resources,
            domain=self.env["resource.reservation"]._enforced_booking_domain(),
        )
        for resource in resources:
            result[resource.id] = booked.get(resource.id, Intervals())
        return result

    def _unavailable_intervals(
        self,
        start_dt: datetime,
        end_dt: datetime,
        resource: ResourceResource | None = None,
        domain: list | None = None,
        tz: ZoneInfo | str | None = None,
    ) -> list[tuple[datetime, datetime]]:
        if resource is None:
            resource = self.env["resource.resource"]
        return self._unavailable_intervals_batch(
            start_dt,
            end_dt,
            resources=resource,
            domain=domain,
            tz=tz,
        )[resource.id]

    def _unavailable_intervals_batch(
        self,
        start_dt: datetime,
        end_dt: datetime,
        resources: ResourceResource | None = None,
        domain: list | None = None,
        tz: ZoneInfo | str | None = None,
    ) -> dict[int | bool, list[tuple[datetime, datetime]]]:
        empty = self.env["resource.resource"]
        resources_list = list(resources) if resources else [empty]
        flexible = empty.union(*(r for r in resources_list if r and r._is_flexible()))
        fixed = [r for r in resources_list if not (r and r._is_flexible())]

        def to_utc(intervals):
            return [
                (start.astimezone(UTC), stop.astimezone(UTC))
                for start, stop in intervals
                if start < stop
            ]

        result = {}
        if flexible:
            leaves = self._leave_intervals_batch(
                start_dt, end_dt, flexible, domain, tz=tz
            )
            blocked = self._hard_reservation_intervals_batch(start_dt, end_dt, flexible)
            for resource in flexible:
                result[resource.id] = to_utc(
                    (start, stop)
                    for start, stop, _meta in (
                        leaves[resource.id] | blocked[resource.id]
                    )
                )
        if fixed:
            work_intervals = self._work_intervals_batch(
                start_dt, end_dt, empty.union(*fixed), domain, tz
            )
            for resource in fixed:
                bounds = [start_dt]
                for start, stop, _meta in work_intervals[resource.id]:
                    bounds += [start, stop]
                bounds.append(end_dt)
                result[resource.id] = to_utc(
                    zip(bounds[0::2], bounds[1::2], strict=True)
                )
        return result

    def _check_overlap(self, attendance_ids: ResourceCalendarAttendance) -> None:
        timed_attendances = [
            attendance
            for attendance in attendance_ids
            if attendance.hour_to > attendance.hour_from
        ]
        result = [
            (
                int(attendance.dayofweek) * 24 + attendance.hour_from + 0.000001,
                int(attendance.dayofweek) * 24 + attendance.hour_to,
                attendance,
            )
            for attendance in timed_attendances
        ]

        if len(Intervals(result)) != len(result):
            raise ValidationError(self.env._("Attendances can't overlap."))

    def _get_attendance_intervals_days_data(
        self, attendance_intervals: Intervals
    ) -> dict[str, float]:
        day_hours = defaultdict(float)
        day_days = defaultdict(float)
        for start, stop, meta in attendance_intervals:
            interval_hours = (stop - start).total_seconds() / 3600
            day_hours[start.date()] += interval_hours
            if len(self) == 1 and self.flexible_hours:
                expected_day_hours = self.hours_per_day or HOURS_PER_DAY
                day_days[start.date()] += min(1.0, interval_hours / expected_day_hours)
            else:
                total_duration_hours = sum(meta.mapped("duration_hours"))
                if total_duration_hours:
                    day_days[start.date()] += (
                        sum(meta.mapped("duration_days"))
                        * interval_hours
                        / total_duration_hours
                    )

        return {
            "days": float_round(sum(day_days.values()), precision_rounding=0.001),
            "hours": sum(day_hours.values()),
        }

    def _get_closest_work_time(
        self,
        dt: datetime,
        match_end: bool = False,
        resource: ResourceResource | None = None,
        search_range: list[datetime] | None = None,
        compute_leaves: bool = True,
    ) -> datetime | None:
        def interval_dt(interval):
            return interval[1 if match_end else 0]

        tz = resource.tz if resource else self.tz
        if resource is None:
            resource = self.env["resource.resource"]

        if not dt.tzinfo or (
            search_range and not (search_range[0].tzinfo and search_range[1].tzinfo)
        ):
            raise ValueError("Provided datetimes needs to be timezoned")

        dt = dt.astimezone(timezone(tz))

        if not search_range:
            range_start = dt + relativedelta(hour=0, minute=0, second=0)
            range_end = dt + relativedelta(days=1, hour=0, minute=0, second=0)
        else:
            range_start, range_end = search_range

        if not range_start <= dt <= range_end:
            return None
        work_intervals = sorted(
            self._work_intervals_batch(
                range_start, range_end, resource, compute_leaves=compute_leaves
            )[resource.id],
            key=lambda i: abs(interval_dt(i) - dt),
        )
        return interval_dt(work_intervals[0]) if work_intervals else None

    def _get_days_per_week(self) -> float:
        self.check_singleton()
        attendances = self._get_global_attendances()
        if self.two_weeks_calendar:
            number_of_days = len(
                set(
                    attendances.filtered(lambda cal: cal.week_type == "1").mapped(
                        "dayofweek"
                    )
                )
            )
            number_of_days += len(
                set(
                    attendances.filtered(lambda cal: cal.week_type == "0").mapped(
                        "dayofweek"
                    )
                )
            )
        else:
            number_of_days = len(set(attendances.mapped("dayofweek")))
        return number_of_days / 2 if self.two_weeks_calendar else number_of_days

    def _get_hours_per_week(self) -> float:
        self.check_singleton()
        hour_count = 0.0
        for attendance in self._get_global_attendances():
            if self.duration_based:
                hour_count += attendance.duration_hours
            else:
                hour_count += attendance.hour_to - attendance.hour_from
        return hour_count / 2 if self.two_weeks_calendar else hour_count

    def _get_hours_per_day(self) -> float:
        hour_per_week = self._get_hours_per_week()
        number_of_days = self._get_days_per_week()
        return hour_per_week / number_of_days if number_of_days else 0

    def _get_global_attendances(self):
        return self.attendance_ids.filtered(
            lambda attendance: (
                attendance.day_period != "lunch" and not attendance.display_type
            )
        )

    def _get_unusual_days(self, start_dt, end_dt, company_id=False):
        if not self:
            return {}
        self.check_singleton()
        if not start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=UTC)
        if not end_dt.tzinfo:
            end_dt = end_dt.replace(tzinfo=UTC)
        # rrule preserves start_dt's time-of-day; anchor on whole days so a
        # later start time never makes the final day drop out of range.
        day_rrule_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_rrule_end = end_dt.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        domain = []
        if company_id:
            domain = [("company_id", "in", (company_id.id, False))]
        if self.flexible_hours:
            leave_intervals = self._leave_intervals_batch(
                start_dt, end_dt, domain=domain
            )[False]
            leave_days = set()
            for start_int, end_int, _ in leave_intervals:
                leave_days.update(
                    start_int.date() + timedelta(days=i)
                    for i in range((end_int.date() - start_int.date()).days + 1)
                )
            return {
                fields.Date.to_string(day.date()): (day.date() in leave_days)
                for day in rrule(DAILY, day_rrule_start, until=day_rrule_end)
            }
        works = {
            d[0].date()
            for d in self._work_intervals_batch(start_dt, end_dt, domain=domain)[False]
        }
        return {
            fields.Date.to_string(day.date()): (day.date() not in works)
            for day in rrule(DAILY, day_rrule_start, until=day_rrule_end)
        }

    def _get_default_attendance_ids(self, company_id=None):
        return [
            Command.create(vals)
            for vals in self._prepare_default_attendance_vals(company_id)
        ]

    def _get_two_weeks_attendance(self, attendance_vals=None):
        if attendance_vals is None:
            attendance_vals = [
                attendance._copy_attendance_vals() for attendance in self.attendance_ids
            ]
        second_week_seq = len(attendance_vals) + 1
        final_attendances = [
            Command.create(
                {
                    "name": "First week",
                    "dayofweek": "0",
                    "sequence": 0,
                    "hour_from": 0,
                    "day_period": "morning",
                    "week_type": "0",
                    "hour_to": 0,
                    "display_type": "line_section",
                }
            ),
            Command.create(
                {
                    "name": "Second week",
                    "dayofweek": "0",
                    "sequence": second_week_seq,
                    "hour_from": 0,
                    "day_period": "morning",
                    "week_type": "1",
                    "hour_to": 0,
                    "display_type": "line_section",
                }
            ),
        ]
        for idx, vals in enumerate(attendance_vals):
            final_attendances.append(
                Command.create(dict(vals, week_type="0", sequence=idx + 1))
            )
            final_attendances.append(
                Command.create(
                    dict(vals, week_type="1", sequence=second_week_seq + idx + 1)
                )
            )
        return final_attendances

    def get_work_hours_count(
        self,
        start_dt: datetime,
        end_dt: datetime,
        compute_leaves: bool = True,
        domain: list | None = None,
    ) -> float:
        # domain filters resource.schedule.exception; it only applies when
        # compute_leaves=True, since compute_leaves=False never reads leaves.
        self.check_singleton()
        if not start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=UTC)
        if not end_dt.tzinfo:
            end_dt = end_dt.replace(tzinfo=UTC)

        if compute_leaves:
            intervals = self._work_intervals_batch(start_dt, end_dt, domain=domain)[
                False
            ]
        else:
            intervals = self._attendance_intervals_batch(start_dt, end_dt)[False]

        return sum(
            (stop - start).total_seconds() / 3600 for start, stop, meta in intervals
        )

    def get_work_duration_data(
        self,
        from_datetime: datetime,
        to_datetime: datetime,
        compute_leaves: bool = True,
        domain: list | None = None,
    ) -> dict[str, float]:
        from_datetime = localized(from_datetime)
        to_datetime = localized(to_datetime)

        if compute_leaves:
            intervals = self._work_intervals_batch(
                from_datetime, to_datetime, domain=domain
            )[False]
        else:
            intervals = self._attendance_intervals_batch(
                from_datetime, to_datetime, domain=domain
            )[False]

        return self._get_attendance_intervals_days_data(intervals)

    def get_attendance_duration_data(
        self,
        from_datetime: datetime,
        to_datetime: datetime,
        domain: list | None = None,
    ) -> dict[str, float]:
        intervals = self._attendance_intervals_batch(
            localized(from_datetime), localized(to_datetime), domain=domain
        )[False]
        return self._get_attendance_intervals_days_data(intervals)

    def _get_hours_for_date(
        self, target_date: date, day_period: str | None = None
    ) -> tuple[float, float]:
        self.check_singleton()
        if not target_date:
            err = "Target Date cannot be empty"
            raise ValueError(err)
        if self.flexible_hours:
            datetimes = [
                12.0 - self.hours_per_day / 2.0,
                12.0,
                12.0 + self.hours_per_day / 2.0,
            ]
            if day_period:
                return (
                    (datetimes[0], datetimes[1])
                    if day_period == "morning"
                    else (datetimes[1], datetimes[2])
                )
            return (datetimes[0], datetimes[2])

        domain = [
            ("calendar_id", "=", self.id),
            ("display_type", "=", False),
            ("day_period", "!=", "lunch"),
        ]

        init_attendances = self.env["resource.calendar.attendance"]._read_group(
            domain=domain,
            groupby=["week_type", "dayofweek", "day_period"],
            aggregates=["hour_from:min", "hour_to:max"],
            order="dayofweek,hour_from:min",
        )

        init_attendances = [
            DummyAttendance(hour_from, hour_to, dayofweek, day_period, week_type)
            for week_type, dayofweek, day_period, hour_from, hour_to in init_attendances
        ]

        if day_period:
            attendances = [
                att for att in init_attendances if att.day_period == day_period
            ]
            attendances.extend(
                attendance._replace(
                    hour_from=(
                        attendance.hour_from
                        if day_period == "morning"
                        else (attendance.hour_from + attendance.hour_to) / 2
                    ),
                    hour_to=(
                        attendance.hour_to
                        if day_period == "afternoon"
                        else (attendance.hour_from + attendance.hour_to) / 2
                    ),
                )
                for attendance in init_attendances
                if attendance.day_period == "full_day"
            )

        else:
            attendances = init_attendances

        week_envelope_from, week_envelope_to = self._week_hours_envelope(attendances)

        week_type = False
        if self.two_weeks_calendar:
            week_type = str(
                self.env["resource.calendar.attendance"].get_week_type(target_date)
            )

        filtered_attendances = [
            att
            for att in attendances
            if att.week_type == week_type
            and int(att.dayofweek) == target_date.weekday()
        ]
        hour_from = min(
            (att.hour_from for att in filtered_attendances), default=week_envelope_from
        )
        hour_to = max(
            (att.hour_to for att in filtered_attendances), default=week_envelope_to
        )

        return (hour_from, hour_to)

    def _get_working_hours(self):
        self.check_singleton()

        working_days = defaultdict(lambda: defaultdict(lambda: False))
        for attendance in self._get_global_attendances():
            working_days[attendance.week_type][attendance.dayofweek] = True
        return working_days

    def _iter_plan_intervals(
        self,
        day_dt: datetime,
        forward: bool,
        compute_leaves: bool,
        domain: list | None,
        resource: ResourceResource,
    ):
        if compute_leaves:
            get_intervals = partial(
                self._work_intervals_batch, domain=domain, resources=resource
            )
            resource_id = resource.id
        else:
            get_intervals = self._attendance_intervals_batch
            resource_id = False
        for n in range(_PLAN_MAX_ITERATIONS):
            if forward:
                dt = day_dt + _PLAN_WINDOW * n
                yield from get_intervals(dt, dt + _PLAN_WINDOW)[resource_id]
            else:
                dt = day_dt - _PLAN_WINDOW * n
                yield from reversed(get_intervals(dt - _PLAN_WINDOW, dt)[resource_id])

    def plan_hours(
        self,
        hours: float,
        day_dt: datetime,
        compute_leaves: bool = False,
        domain: list | None = None,
        resource: ResourceResource | None = None,
    ) -> datetime | bool:
        revert = to_timezone(day_dt.tzinfo)
        day_dt = localized(day_dt)
        if resource is None:
            resource = self.env["resource.resource"]
        forward = hours >= 0
        hours = abs(hours)
        for start, stop, _meta in self._iter_plan_intervals(
            day_dt, forward, compute_leaves, domain, resource
        ):
            interval_hours = (stop - start).total_seconds() / 3600
            if hours <= interval_hours:
                if forward:
                    return revert(start + timedelta(hours=hours))
                return revert(stop - timedelta(hours=hours))
            hours -= interval_hours
        return False

    def plan_days(
        self,
        days: int,
        day_dt: datetime,
        compute_leaves: bool = False,
        domain: list | None = None,
        resource: ResourceResource | None = None,
    ) -> datetime | bool:
        revert = to_timezone(day_dt.tzinfo)
        day_dt = localized(day_dt)
        if resource is None:
            resource = self.env["resource.resource"]
        if not days:
            return revert(day_dt)
        forward = days > 0
        days = abs(days)
        found = set()
        boundary = None
        for start, stop, _meta in self._iter_plan_intervals(
            day_dt, forward, compute_leaves, domain, resource
        ):
            if start.date() not in found:
                if len(found) == days:
                    return revert(boundary)
                found.add(start.date())
            boundary = stop if forward else start
        return False

    def _prepare_default_attendance_vals(self, company_id=None):
        if company_id and (
            attendances := company_id.resource_calendar_id.attendance_ids
        ):
            return [attendance._copy_attendance_vals() for attendance in attendances]
        default_days = (
            (
                "0",
                self.env._("Monday Morning"),
                self.env._("Monday Lunch"),
                self.env._("Monday Afternoon"),
            ),
            (
                "1",
                self.env._("Tuesday Morning"),
                self.env._("Tuesday Lunch"),
                self.env._("Tuesday Afternoon"),
            ),
            (
                "2",
                self.env._("Wednesday Morning"),
                self.env._("Wednesday Lunch"),
                self.env._("Wednesday Afternoon"),
            ),
            (
                "3",
                self.env._("Thursday Morning"),
                self.env._("Thursday Lunch"),
                self.env._("Thursday Afternoon"),
            ),
            (
                "4",
                self.env._("Friday Morning"),
                self.env._("Friday Lunch"),
                self.env._("Friday Afternoon"),
            ),
        )
        periods = (("morning", 8, 12), ("lunch", 12, 13), ("afternoon", 13, 17))
        return [
            {
                "name": name,
                "dayofweek": dayofweek,
                "hour_from": hour_from,
                "hour_to": hour_to,
                "day_period": day_period,
            }
            for dayofweek, *names in default_days
            for (day_period, hour_from, hour_to), name in zip(
                periods, names, strict=True
            )
        ]

    @staticmethod
    def _single_week_attendance_vals(attendance_vals):
        return [
            dict(vals, week_type=False)
            for vals in attendance_vals
            if not vals.get("display_type") and vals.get("week_type") != "1"
        ]

    def _works_on_date(self, date: date) -> bool:
        self.check_singleton()

        working_days = self._get_working_hours()
        dayofweek = str(date.weekday())
        if self.two_weeks_calendar:
            weektype = str(self.env["resource.calendar.attendance"].get_week_type(date))
            return working_days[weektype][dayofweek]
        return working_days[False][dayofweek]

    @staticmethod
    def _week_hours_envelope(attendances) -> tuple[float, float]:
        return (
            min((att.hour_from for att in attendances), default=0.0),
            max((att.hour_to for att in attendances), default=0.0),
        )
