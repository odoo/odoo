from collections import defaultdict
from datetime import UTC, datetime, timedelta

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.intervals import Intervals, _iter_boundaries, invert_intervals
from odoo.libs.numbers import float_compare
from odoo.tools.date_utils import float_to_time, get_intervals_hours

from ..tools import debug_log as dbg


def _record_overlap_intervals(intervals):
    boundaries = sorted(_iter_boundaries(intervals, "start", "stop"))
    counts = {}
    interval_vals = []
    ids = set()
    start = None
    for time, flag, records in boundaries:
        for record in records:
            if new_count := counts.get(record.id, 0) + {"start": 1, "stop": -1}[flag]:
                counts[record.id] = new_count
            else:
                del counts[record.id]
        new_ids = set(counts.keys())
        if ids != new_ids:
            if ids and start is not None:
                interval_vals.append((start, time, records.browse(ids)))
            if new_ids:
                start = time
        ids = new_ids
    return Intervals(interval_vals, keep_distinct=True)


def _time_delta_hours(td):
    return td.total_seconds() / 3600


class HrAttendanceOvertimeRule(models.Model):
    _name = "hr.attendance.overtime.rule"
    _description = "Overtime Rule"

    name = fields.Char(required=True)
    description = fields.Html()
    base_off = fields.Selection(
        selection=[
            ("quantity", "Quantity"),
            ("timing", "Timing"),
        ],
        string="Based Off",
        default="quantity",
        required=True,
        help="Base for overtime calculation.\n"
        "Use 'Quantity' when overtime hours are those in excess of a certain amount per day/week.\n"
        "Use 'Timing' when overtime hours happen on specific days or at specific times",
    )

    timing_type = fields.Selection(
        selection=[
            ("work_days", "On any working day"),
            ("non_work_days", "On any non-working day"),
            ("leave", "When employee is off"),
            ("schedule", "Outside of a specific schedule"),
        ],
        default="work_days",
    )
    timing_start = fields.Float(
        string="From",
        default=0,
    )
    timing_stop = fields.Float(
        string="To",
        default=24,
    )
    expected_hours_from_contract = fields.Boolean(
        string="Hours from employee schedule",
        default=True,
        help="When enabled, expected hours are derived from the employee's contract/schedule instead of the fixed 'Expected Hours' value. With Absence Management enabled, this also allows the attendance to go into negative extra hours to represent hours missing compared to what is expected.",
    )

    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Schedule",
        domain=[("flexible_hours", "=", False)],
    )

    expected_hours = fields.Float(string="Usual work hours")
    quantity_period = fields.Selection(
        selection=[("day", "Day"), ("week", "Week")],
        default="day",
    )
    sequence = fields.Integer(default=10)

    ruleset_id = fields.Many2one(
        comodel_name="hr.attendance.overtime.ruleset",
        index=True,
        required=True,
    )
    company_id = fields.Many2one(related="ruleset_id.company_id")

    paid = fields.Boolean(string="Pay Extra Hours")
    amount_rate = fields.Float(
        string="Rate",
        default=1.0,
    )

    employee_tolerance = fields.Float()
    employer_tolerance = fields.Float()

    information_display = fields.Char(
        string="Information",
        compute="_compute_information_display",
    )

    _timing_start_is_hour = models.Constraint(
        "CHECK(0 <= timing_start AND timing_start < 24)",
        "Timing Start is an hour of the day",
    )
    _timing_stop_is_hour = models.Constraint(
        "CHECK(0 <= timing_stop AND timing_stop <= 24)",
        "Timing Stop is an hour of the day",
    )

    @api.constrains(
        "base_off", "expected_hours", "expected_hours_from_contract", "quantity_period"
    )
    def _check_expected_hours(self):
        for rule in self:
            if (
                rule.base_off == "quantity"
                and not rule.expected_hours_from_contract
                and not rule.expected_hours
            ):
                raise ValidationError(
                    self.env._(
                        "Rule '%(name)s' is based off quantity, but the usual amount of work hours is not specified",
                        name=rule.name,
                    )
                )

            if rule.base_off == "quantity" and not rule.quantity_period:
                raise ValidationError(
                    self.env._(
                        "Rule '%(name)s' is based off quantity, but the period is not specified",
                        name=rule.name,
                    )
                )

    @api.constrains("base_off", "timing_type", "resource_calendar_id")
    def _check_work_schedule(self):
        for rule in self:
            if (
                rule.base_off == "timing"
                and rule.timing_type == "schedule"
                and not rule.resource_calendar_id
            ):
                raise ValidationError(
                    self.env._(
                        "Rule '%(name)s' is based off timing, but the work schedule is not specified",
                        name=rule.name,
                    )
                )

    def _get_expected_hours_for_period(self, start, stop, schedule, employee):
        self.check_singleton()
        period = Intervals([(start, stop, self.env["resource.calendar"])])
        return get_intervals_hours((schedule["work"] - schedule["leave"]) & period)

    def _get_daterange_overtime_undertime_intervals_for_quantity_rule(
        self, start, stop, attendance_intervals, schedule
    ):
        self.check_singleton()
        expected_duration = self.expected_hours
        attendances_interval_without_lunch = []
        intervals_attendance_by_attendance = defaultdict(Intervals)
        attendances = self.env["hr.attendance"]
        for a_start, a_stop, attendance in attendance_intervals:
            attendances += attendance
            intervals_attendance_by_attendance[attendance] = (
                Intervals([(a_start, a_stop, self.env["resource.calendar"])])
                - (schedule["lunch"] - schedule["leave"])
            ) & Intervals([(start, stop, self.env["resource.calendar"])])
            attendances_interval_without_lunch.extend(
                intervals_attendance_by_attendance[attendance]._items
            )

        if self.expected_hours_from_contract:
            expected_duration = self._get_expected_hours_for_period(
                start, stop, schedule, attendances.employee_id
            )

        worked_amount = get_intervals_hours(
            Intervals(attendances_interval_without_lunch)
        )
        overtime_amount = worked_amount - expected_duration
        dbg.logic.debug(
            "rule %s (%s/%s) %s..%s: worked %.3fh vs expected %.3fh -> %.3fh",
            dbg.rec(self),
            self.base_off,
            self.quantity_period,
            start,
            stop,
            worked_amount,
            expected_duration,
            overtime_amount,
        )
        employee = attendances.employee_id
        company = self.company_id or employee.company_id
        if (
            company.absence_management
            and float_compare(overtime_amount, -self.employee_tolerance, 5) == -1
        ):
            last_attendance = max(
                intervals_attendance_by_attendance.keys(), key=lambda att: att.check_out
            )
            dbg.logic.debug(
                "rule %s: undertime %.3fh charged to %s",
                dbg.rec(self),
                overtime_amount,
                dbg.rec(last_attendance),
            )
            return {}, {last_attendance: [(overtime_amount, self)]}

        if float_compare(overtime_amount, self.employer_tolerance, 5) != 1:
            dbg.logic.debug(
                "rule %s: %.3fh within the employer tolerance %.3fh, no line",
                dbg.rec(self),
                overtime_amount,
                self.employer_tolerance,
            )
            return {}, {}

        overtime_intervals = defaultdict(list)
        remaining_duration = expected_duration
        remaining_overtime_amount = overtime_amount
        for attendance in attendances.sorted("check_in"):
            for (
                interval_start,
                interval_stop,
                _cal,
            ) in intervals_attendance_by_attendance[attendance]:
                interval_duration = (
                    interval_stop - interval_start
                ).total_seconds() / 3600
                if remaining_duration >= interval_duration:
                    remaining_duration -= interval_duration
                    continue
                interval_overtime_duration = interval_duration
                if remaining_duration != 0:
                    interval_overtime_duration = interval_duration - remaining_duration
                new_start = interval_stop - timedelta(hours=interval_overtime_duration)
                remaining_duration = 0
                overtime_intervals[attendance].append((new_start, interval_stop, self))
                remaining_overtime_amount -= interval_overtime_duration
                if remaining_overtime_amount <= 0:
                    return overtime_intervals, {}
        return overtime_intervals, {}

    def _get_all_overtime_undertime_intervals_for_quantity_rule(
        self, attendances_by_periods_by_employee, schedule_by_employee
    ):
        def _merge_overtime_dict(d1, d2):
            for attendance, overtime_list in d2.items():
                d1[attendance].extend(overtime_list)

        overtime_by_employee_by_attendance = defaultdict(lambda: defaultdict(list))
        undertime_by_employee_by_attendance = defaultdict(lambda: defaultdict(list))
        for (
            employee,
            duration_and_amount_by_periods,
        ) in attendances_by_periods_by_employee.items():
            schedule = schedule_by_employee["schedule"][employee]
            schedule["leave"] = schedule_by_employee["leave"][employee]
            fully_flex_schedule = schedule_by_employee["fully_flexible"][employee]
            for day, attendance_interval in duration_and_amount_by_periods.items():
                for rule in self:
                    start = datetime.combine(day, datetime.min.time())
                    if rule.quantity_period == "week":
                        start -= relativedelta(days=6)
                    stop = datetime.combine(day, datetime.max.time())
                    if not (
                        Intervals([(start, stop, self.env["resource.calendar"])])
                        - fully_flex_schedule
                    ):
                        continue
                    (
                        rule_overtime_list_by_attendance,
                        rule_undertime_list_by_attendance,
                    ) = rule._get_daterange_overtime_undertime_intervals_for_quantity_rule(
                        start, stop, attendance_interval, schedule
                    )
                    _merge_overtime_dict(
                        overtime_by_employee_by_attendance[employee],
                        rule_overtime_list_by_attendance,
                    )
                    _merge_overtime_dict(
                        undertime_by_employee_by_attendance[employee],
                        rule_undertime_list_by_attendance,
                    )
        return overtime_by_employee_by_attendance, undertime_by_employee_by_attendance

    def _get_rules_intervals_by_timing_type(
        self, min_check_in, max_check_out, employees, schedules_intervals_by_employee
    ):

        def _generate_days_intervals(intervals):
            days_intervals = []
            dates = set()
            for interval in intervals:
                start_datetime = interval[0]
                if start_datetime.time() == datetime.max.time():
                    start_datetime += relativedelta(days=1)
                start_day = start_datetime.date()
                stop_datetime = interval[1]
                if stop_datetime.time() == datetime.min.time():
                    stop_datetime -= relativedelta(days=1)
                stop_day = stop_datetime.date()
                if stop_day < start_day:
                    continue
                start = datetime.combine(start_day, datetime.min.time())
                stop = datetime.combine(stop_day, datetime.max.time())
                dates.update(
                    day.date() for day in rrule(freq=DAILY, dtstart=start, until=stop)
                )
            days_intervals.extend(
                (
                    datetime.combine(date, datetime.min.time()),
                    datetime.combine(date, datetime.max.time()),
                    self.env["resource.calendar"],
                )
                for date in dates
            )
            return Intervals(days_intervals, keep_distinct=True)

        def _invert_intervals(intervals, first_start, last_stop):
            items = []
            prev_stop = first_start
            if not intervals:
                return Intervals(
                    [(first_start, last_stop, self.env["resource.calendar"])]
                )
            no_record = self.env["resource.calendar"]
            for start, stop, _record in sorted(intervals):
                if (
                    prev_stop
                    and prev_stop < start
                    and (
                        float_compare(
                            (last_stop - start).total_seconds(), 0, precision_digits=1
                        )
                        >= 0
                    )
                ):
                    items.append((prev_stop, start, no_record))
                prev_stop = max(prev_stop, stop)
            if last_stop and prev_stop < last_stop:
                items.append((prev_stop, last_stop, no_record))
            return Intervals(items, keep_distinct=True)

        timing_rule_by_timing_type = self.grouped("timing_type")
        timing_type_set = set(timing_rule_by_timing_type.keys())

        intervals_by_timing_type = {
            "leave": schedules_intervals_by_employee["leave"],
            "schedule": defaultdict(lambda: defaultdict(Intervals)),
            "work_days": defaultdict(),
            "non_work_days": defaultdict(),
        }

        for employee in employees:
            if {"work_days", "non_work_days"} & timing_type_set:
                intervals_by_timing_type["work_days"][employee] = (
                    _generate_days_intervals(
                        schedules_intervals_by_employee["schedule"][employee]["work"]
                        - schedules_intervals_by_employee["leave"][employee]
                    )
                )
            if "non_work_days" in timing_type_set:
                intervals_by_timing_type["non_work_days"][employee] = (
                    _generate_days_intervals(
                        _invert_intervals(
                            intervals_by_timing_type["work_days"][employee],
                            datetime.combine(min_check_in, datetime.min.time()),
                            datetime.combine(max_check_out, datetime.max.time()),
                        )
                    )
                )
        if "schedule" in timing_type_set:
            for calendar in timing_rule_by_timing_type["schedule"].resource_calendar_id:
                start_datetime = datetime.combine(
                    min_check_in, datetime.min.time()
                ).replace(tzinfo=UTC) - relativedelta(days=1)
                stop_datetime = datetime.combine(
                    max_check_out, datetime.max.time()
                ).replace(tzinfo=UTC) + relativedelta(days=1)
                interval = calendar._attendance_intervals_batch(
                    start_datetime, stop_datetime, lunch=True
                )[False]
                interval |= calendar._attendance_intervals_batch(
                    start_datetime, stop_datetime
                )[False]
                naive_interval = Intervals(
                    [
                        (
                            i_start.replace(tzinfo=None),
                            i_stop.replace(tzinfo=None),
                            i_model,
                        )
                        for i_start, i_stop, i_model in interval._items
                    ]
                )
                calendar_intervals = _invert_intervals(
                    naive_interval,
                    start_datetime.replace(tzinfo=None),
                    stop_datetime.replace(tzinfo=None),
                )
                intervals_by_timing_type["schedule"][calendar.id].update(
                    dict.fromkeys(employees, calendar_intervals)
                )
        return intervals_by_timing_type

    def _get_all_overtime_intervals_for_timing_rule(
        self, min_check_in, max_check_out, attendances, schedules_intervals_by_employee
    ):

        def update_overtime(employees, rules, intervals, attendances_intervals):
            if not intervals:
                return
            for employee in employees:
                intersection_interval_for_attendance = (
                    attendances_intervals[employee] & intervals[employee]
                )
                overtime_interval_list = defaultdict(list)
                for start, stop, attendance in intersection_interval_for_attendance:
                    overtime_interval_list[attendance].append((start, stop, rules))
                for (
                    attendance,
                    attendance_intervals_list,
                ) in overtime_interval_list.items():
                    overtime_by_employee_by_attendance[employee][attendance] |= (
                        Intervals(attendance_intervals_list)
                    )

        def get_day_rule_intervals(employees, rule, intervals):
            timing_intervals_by_employee = defaultdict(Intervals)
            start = min(rule.timing_start, rule.timing_stop)
            stop = max(rule.timing_start, rule.timing_stop)
            for employee in employees:
                for interval in intervals[employee]:
                    start_datetime = datetime.combine(
                        interval[0].date(), float_to_time(start)
                    )
                    stop_datetime = datetime.combine(
                        interval[0].date(), float_to_time(stop)
                    )
                    timing_intervals = Intervals(
                        [(start_datetime, stop_datetime, self.env["resource.calendar"])]
                    )
                    if rule.timing_start > rule.timing_stop:
                        day_start = datetime.combine(
                            interval[0].date(), datetime.min.time()
                        )
                        day_end = datetime.combine(
                            interval[0].date(), datetime.max.time()
                        )
                        timing_intervals = Intervals(
                            [
                                (i_start, i_stop, self.env["resource.calendar"])
                                for i_start, i_stop in invert_intervals(
                                    [(start_datetime, stop_datetime)],
                                    day_start,
                                    day_end,
                                )
                            ]
                        )
                    timing_intervals_by_employee[employee] |= timing_intervals
            return timing_intervals_by_employee

        employees = attendances.employee_id
        intervals_by_timing_type = self._get_rules_intervals_by_timing_type(
            min_check_in, max_check_out, employees, schedules_intervals_by_employee
        )
        attendances_intervals_by_employee = defaultdict()
        overtime_by_employee_by_attendance = defaultdict(lambda: defaultdict(Intervals))

        attendances_by_employee = attendances.grouped("employee_id")
        for employee, emp_attendance in attendances_by_employee.items():
            attendances_intervals_by_employee[employee] = Intervals(
                [
                    (*(attendance._get_localized_times()), attendance)
                    for attendance in emp_attendance
                ],
                keep_distinct=True,
            )

        for timing_type, rules in self.grouped("timing_type").items():
            if timing_type == "leave":
                update_overtime(
                    employees,
                    rules,
                    intervals_by_timing_type["leave"],
                    attendances_intervals_by_employee,
                )

            elif timing_type == "schedule":
                for calendar, calendar_rules in rules.grouped(
                    "resource_calendar_id"
                ).items():
                    outside_calendar_intervals = intervals_by_timing_type["schedule"][
                        calendar.id
                    ]
                    update_overtime(
                        employees,
                        calendar_rules,
                        outside_calendar_intervals,
                        attendances_intervals_by_employee,
                    )
            else:
                for rule in rules:
                    timing_intervals_by_employee = get_day_rule_intervals(
                        employees, rule, intervals_by_timing_type[timing_type]
                    )
                    update_overtime(
                        employees,
                        rule,
                        timing_intervals_by_employee,
                        attendances_intervals_by_employee,
                    )
        return overtime_by_employee_by_attendance

    def _get_overtime_undertime_intervals_by_employee_by_attendance(
        self, min_check_in, max_check_out, attendances, schedules_intervals_by_employee
    ):

        def _merge_overtime_dict(d1, d2):
            for employee, overtime_interval_list in d2.items():
                for attendance, overtime_list in overtime_interval_list.items():
                    d1[employee][attendance].extend(overtime_list)

        overtime_by_employee_by_attendance = defaultdict(lambda: defaultdict(list))
        undertime_by_employee_by_attendance = defaultdict(lambda: defaultdict(list))

        quantity_rules = self.filtered_domain([("base_off", "=", "quantity")])
        if quantity_rules:
            attendances_by_periods_by_employee = (
                attendances._get_attendance_by_periods_by_employee()
            )
            quantity_rule_by_periods = quantity_rules.grouped("quantity_period")
            for period, rules in quantity_rule_by_periods.items():
                (
                    quantity_overtime_by_employee_by_attendance,
                    quantity_undertime_by_employee_by_attendance,
                ) = rules._get_all_overtime_undertime_intervals_for_quantity_rule(
                    attendances_by_periods_by_employee[period],
                    schedules_intervals_by_employee,
                )
                _merge_overtime_dict(
                    overtime_by_employee_by_attendance,
                    quantity_overtime_by_employee_by_attendance,
                )
                _merge_overtime_dict(
                    undertime_by_employee_by_attendance,
                    quantity_undertime_by_employee_by_attendance,
                )

        timing_rules = self - quantity_rules
        if not timing_rules:
            return (
                overtime_by_employee_by_attendance,
                undertime_by_employee_by_attendance,
            )

        _merge_overtime_dict(
            overtime_by_employee_by_attendance,
            timing_rules._get_all_overtime_intervals_for_timing_rule(
                min_check_in,
                max_check_out,
                attendances,
                schedules_intervals_by_employee,
            ),
        )
        return overtime_by_employee_by_attendance, undertime_by_employee_by_attendance

    @dbg.timed
    def _generate_overtime_vals(
        self, min_check_in, max_check_out, attendances, schedules_intervals_by_employee
    ):
        vals = []

        def _add_overtime_val(attendance, duration_by_day_by_rules):
            for day, duration_by_rules in duration_by_day_by_rules.items():
                for rules, duration in duration_by_rules.items():
                    vals.append(
                        {
                            "attendance_id": attendance.id,
                            "time_start": attendance.check_in,
                            "time_stop": attendance.check_out,
                            "duration": round(duration, 3),
                            "employee_id": attendance.employee_id.id,
                            "date": day,
                            "rule_ids": rules.ids,
                            **rules._extra_overtime_vals(),
                        }
                    )

        overtimes, undertimes = (
            self._get_overtime_undertime_intervals_by_employee_by_attendance(
                min_check_in,
                max_check_out,
                attendances,
                schedules_intervals_by_employee,
            )
        )
        for intervals_by_attendance in overtimes.values():
            for attendance, intervals in intervals_by_attendance.items():
                duration_by_day_by_rules = defaultdict(lambda: defaultdict(float))
                record_overlap_intervals = _record_overlap_intervals(intervals)
                for start, stop, rules in record_overlap_intervals:
                    date = start.date()
                    duration_by_day_by_rules[date][rules] += (
                        stop - start
                    ).total_seconds() / 3600
                _add_overtime_val(attendance, duration_by_day_by_rules)

        dbg.pipeline.debug(
            "_generate_overtime_vals: %d rule(s) over %s produced %d overtime val(s)",
            len(self),
            dbg.rec(attendances),
            len(vals),
        )
        for intervals_by_attendance in undertimes.values():
            for attendance, intervals in intervals_by_attendance.items():
                date = attendance.date
                duration_by_day_by_rules = defaultdict(lambda: defaultdict(float))
                # Several quantity rules can each report a shortfall for the
                # same day; the smallest shortfall is the one owed.
                duration, rules = max(intervals, key=lambda x: x[0])
                duration_by_day_by_rules[date][rules] += duration
                _add_overtime_val(attendance, duration_by_day_by_rules)
        return vals

    def _extra_overtime_vals(self):
        self.ruleset_id.check_singleton()
        paid_rules = self.filtered("paid")
        if not paid_rules:
            return {"amount_rate": 0.0}

        rates = paid_rules.mapped("amount_rate")
        if self.ruleset_id.rate_combination_mode == "sum":
            return {"amount_rate": sum(rate - 1.0 for rate in rates) + 1.0}
        return {"amount_rate": max(rates)}

    @api.depends(
        "base_off",
        "expected_hours_from_contract",
        "expected_hours",
        "quantity_period",
        "timing_type",
        "resource_calendar_id",
    )
    def _compute_information_display(self):
        timing_types = dict(self._fields["timing_type"].selection)
        for rule in self:
            if rule.base_off == "quantity":
                if rule.expected_hours_from_contract:
                    rule.information_display = self.env._("From Employee")
                    continue
                rule.information_display = self.env._(
                    "%(nb_hours)d h / %(period)s",
                    nb_hours=rule.expected_hours,
                    period={
                        "day": self.env._("day"),
                        "week": self.env._("week"),
                    }[rule.quantity_period],
                )
            else:
                if rule.timing_type == "schedule":
                    rule.information_display = self.env._(
                        "Outside Schedule: %(schedule_name)s",
                        schedule_name=rule.resource_calendar_id.name,
                    )
                    continue
                rule.information_display = timing_types[rule.timing_type]
