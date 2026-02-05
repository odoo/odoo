# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import float_to_time, sum_intervals
from odoo.tools.float_utils import float_compare
from odoo.tools.intervals import Intervals, _boundaries, invert_intervals


def _naive_utc(dt):
    return dt.astimezone(UTC).replace(tzinfo=None)


def _midnight(date):
    return datetime.combine(date, datetime.min.time())


def _record_overlap_intervals(intervals):
    boundaries = sorted(_boundaries(intervals, 'start', 'stop'))
    counts = {}
    interval_vals = []
    ids = set()
    start = None
    for (time, flag, records) in boundaries:
        for record in records:
            if (
                new_count := counts.get(record.id, 0) + {'start': 1, 'stop': -1}[flag]
            ):
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


class HrAttendanceOvertimeRule(models.Model):
    _name = 'hr.attendance.overtime.rule'
    _description = "Overtime Rule"

    name = fields.Char(required=True)
    description = fields.Html()
    base_off = fields.Selection([
            ('quantity', "Quantity"),
            ('timing', "Timing"),
        ],
        string="Based Off",
        required=True,
        default='quantity',
        help=(
            "Base for overtime calculation.\n"
            "Use 'Quantity' when overtime hours are those in excess of a certain amount per day/week.\n"
            "Use 'Timing' when overtime hours happen on specific days or at specific times"
        ),
    )

    timing_type = fields.Selection([
        ('work_days', "On any working day"),
        ('non_work_days', "On any non-working day"),
        ('leave', "When employee is off"),
        ('public_leave', "On a Public holiday"),
        ('schedule', "Outside of a specific schedule"),
    ], default='work_days')
    timing_start = fields.Float("From", default=0)
    timing_stop = fields.Float("To", default=24)
    expected_hours_from_contract = fields.Boolean(
        "Hours from employee schedule",
        default=True,
        help="The attendance can go into negative extra hours to represent the missing hours compared to what is expected if the Absence Management setting is enabled.",
    )

    resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string="Schedule",
    )

    expected_hours = fields.Float(string="Usual work hours")
    quantity_period = fields.Selection([
            ('day', 'Day'),
            ('week', 'Week')
        ],
        default='day',
    )
    sequence = fields.Integer(default=10)

    ruleset_id = fields.Many2one('hr.attendance.overtime.ruleset', required=True, index=True)
    company_id = fields.Many2one(related='ruleset_id.company_id')

    paid = fields.Boolean("Pay Extra Hours")
    amount_rate = fields.Float("Rate", default=1.0)

    employee_tolerance = fields.Float()
    employer_tolerance = fields.Float()

    information_display = fields.Char("Information", compute='_compute_information_display')

    _timing_start_is_hour = models.Constraint(
        'CHECK(0 <= timing_start AND timing_start < 24)',
        "Timing Start is an hour of the day",
    )
    _timing_stop_is_hour = models.Constraint(
        'CHECK(0 <= timing_stop AND timing_stop <= 24)',
        "Timing Stop is an hour of the day",
    )

    # Quantity rule well defined
    @api.constrains('base_off', 'expected_hours', 'quantity_period')
    def _check_expected_hours(self):
        for rule in self:
            if (
                rule.base_off == 'quantity'
                and not rule.expected_hours_from_contract
                and not rule.expected_hours
            ):
                raise ValidationError(self.env._("Rule '%(name)s' is based off quantity, but the usual amount of work hours is not specified", name=rule.name))

            if rule.base_off == 'quantity' and not rule.quantity_period:
                raise ValidationError(self.env._("Rule '%(name)s' is based off quantity, but the period is not specified", name=rule.name))

    # Timing rule well defined
    @api.constrains('base_off', 'timing_type', 'resource_calendar_id')
    def _check_work_schedule(self):
        for rule in self:
            if (
                rule.base_off == 'timing'
                and rule.timing_type == 'schedule'
                and not rule.resource_calendar_id
            ):
                raise ValidationError(self.env._("Rule '%(name)s' is based off timing, but the work schedule is not specified", name=rule.name))

    def _get_daterange_overtime_undertime_intervals_for_quantity_rule(self, start, stop, attendance_intervals, schedule):
        self.ensure_one()
        expected_duration = self.expected_hours
        attendances_interval = []
        intervals_attendance_by_attendance = defaultdict(Intervals)
        attendances = self.env['hr.attendance']
        for (a_start, a_stop, attendance) in attendance_intervals:
            attendances += attendance
            intervals_attendance_by_attendance[attendance] = Intervals([(a_start, a_stop, self.env['resource.calendar'])]) &\
                Intervals([(start, stop, self.env['resource.calendar'])])
            attendances_interval.extend(intervals_attendance_by_attendance[attendance]._items)

        if self.expected_hours_from_contract:
            period_schedule = schedule & Intervals([(start, stop, self.env['resource.calendar'])])
            expected_duration = sum_intervals(period_schedule)

        overtime_amount = sum_intervals(Intervals(attendances_interval)) - expected_duration
        employee = attendances.employee_id
        company = self.company_id or employee.company_id
        if company.absence_management and float_compare(overtime_amount, -self.employee_tolerance, 5) == -1:
            last_attendance = sorted(intervals_attendance_by_attendance.keys(), key=lambda att: att.check_out)[-1]
            return {}, {last_attendance: [(overtime_amount, self)]}

        if float_compare(overtime_amount, self.employer_tolerance, 5) != 1:
            return {}, {}

        overtime_intervals = defaultdict(list)
        remaining_duration = expected_duration
        remanining_overtime_amount = overtime_amount
        # Attendances are sorted by check_in asc
        for attendance in attendances.sorted('check_in'):
            for start, stop, _cal in intervals_attendance_by_attendance[attendance]:
                interval_duration = (stop - start).total_seconds() / 3600
                if remaining_duration >= interval_duration:
                    remaining_duration -= interval_duration
                    continue
                interval_overtime_duration = interval_duration
                if remaining_duration != 0:
                    interval_overtime_duration = interval_duration - remaining_duration
                new_start = stop - timedelta(hours=interval_overtime_duration)
                remaining_duration = 0
                overtime_intervals[attendance].append((new_start, stop, self))
                remanining_overtime_amount = remanining_overtime_amount - interval_overtime_duration
                if remanining_overtime_amount <= 0:
                    return overtime_intervals, {}
        return overtime_intervals, {}

    def _get_all_overtime_undertime_intervals_for_quantity_rule(self, attendances_by_periods_by_employee, schedule_by_employee):
        def _merge_overtime_dict(d1, d2):
            for attendance, overtime_list in d2.items():
                d1[attendance].extend(overtime_list)

        overtime_by_employee_by_attendance = defaultdict(lambda: defaultdict(list))
        undertime_by_employee_by_attendance = defaultdict(lambda: defaultdict(list))
        for employee, duration_and_amount_by_periods in attendances_by_periods_by_employee.items():
            schedule = schedule_by_employee['schedule'][employee] - schedule_by_employee['leave'][employee]
            fully_flex_schedule = schedule_by_employee['fully_flexible'][employee]
            for day, attendance_interval in duration_and_amount_by_periods.items():
                for rule in self:
                    start = datetime.combine(day, datetime.min.time())
                    if rule.quantity_period == 'week':
                        start -= relativedelta(days=6)
                    stop = datetime.combine(day, datetime.max.time())
                    if not (Intervals([(start, stop, self.env['resource.calendar'])]) - fully_flex_schedule):  # employee is fully flexible
                        continue
                    rule_overtime_list_by_attendance, rule_undertime_list_by_attendance = rule._get_daterange_overtime_undertime_intervals_for_quantity_rule(start, stop, attendance_interval, schedule & Intervals([(start, stop, self.env['resource.calendar'])]))
                    _merge_overtime_dict(overtime_by_employee_by_attendance[employee], rule_overtime_list_by_attendance)
                    _merge_overtime_dict(undertime_by_employee_by_attendance[employee], rule_undertime_list_by_attendance)
        return overtime_by_employee_by_attendance, undertime_by_employee_by_attendance

    def _get_rules_intervals_by_timing_type(self, min_check_in, max_check_out, employees, schedules_intervals_by_employee):

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
                for day in rrule(freq=DAILY, dtstart=start, until=stop):
                    dates.add(day.date())
            for date in dates:
                days_intervals.append(
                    (
                        datetime.combine(date, datetime.min.time()),
                        datetime.combine(date, datetime.max.time()),
                        self.env['resource.calendar']
                    )
                )
            return Intervals(days_intervals, keep_distinct=True)

        def _invert_intervals(intervals, first_start, last_stop):
            # Redefintion of the method to return an interval
            items = []
            prev_stop = first_start
            if not intervals:
                return Intervals([(first_start, last_stop, self.env['resource.calendar'])])
            for start, stop, record in sorted(intervals):
                if prev_stop and prev_stop < start and (float_compare((last_stop - start).total_seconds(), 0, precision_digits=1) >= 0):
                    items.append((prev_stop, start, record))
                prev_stop = max(prev_stop, stop)
            if last_stop and prev_stop < last_stop:
                items.append((prev_stop, last_stop, record))
            return Intervals(items, keep_distinct=True)

        timing_rule_by_timing_type = self.grouped('timing_type')
        timing_type_set = set(timing_rule_by_timing_type.keys())

        intervals_by_timing_type = {
            'leave': schedules_intervals_by_employee['leave'],
            'schedule': defaultdict(lambda: defaultdict(Intervals)),
            'work_days': defaultdict(),
            'non_work_days': defaultdict(),
            'public_leave': defaultdict(),
        }

        for employee in employees:
            if {'work_days', 'non_work_days'} & timing_type_set:
                intervals_by_timing_type['work_days'][employee] = _generate_days_intervals(
                    schedules_intervals_by_employee['schedule'][employee] - schedules_intervals_by_employee['leave'][employee]
                )
            if 'non_work_days' in timing_type_set:
                intervals_by_timing_type['non_work_days'][employee] = _generate_days_intervals(
                    _invert_intervals(
                        intervals_by_timing_type['work_days'][employee],
                        datetime.combine(min_check_in, datetime.min.time()),
                        datetime.combine(max_check_out, datetime.max.time())
                    )
                )
            if 'public_leave' in timing_type_set:
                intervals_by_timing_type['public_leave'][employee] = _generate_days_intervals(schedules_intervals_by_employee['public_leave'][employee])

        if 'schedule' in timing_type_set:
            for calendar in timing_rule_by_timing_type['schedule'].resource_calendar_id:
                start_datetime = datetime.combine(min_check_in, datetime.min.time()).replace(tzinfo=UTC) - relativedelta(days=1)  # to avoid timezone shift
                stop_datetime = datetime.combine(max_check_out, datetime.max.time()).replace(tzinfo=UTC) + relativedelta(days=1)  # to avoid timezone shift
                interval = calendar._attendance_intervals_batch(start_datetime, stop_datetime)[False]
                naive_interval = Intervals([(
                    i_start.replace(tzinfo=None),
                    i_stop.replace(tzinfo=None),
                    i_model
                ) for i_start, i_stop, i_model in interval._items])
                calendar_intervals = _invert_intervals(
                    naive_interval,
                    start_datetime.replace(tzinfo=None),
                    stop_datetime.replace(tzinfo=None)
                )
                intervals_by_timing_type['schedule'][calendar.id].update(
                    {employee: calendar_intervals for employee in employees}
                )
        return intervals_by_timing_type

    def _get_all_overtime_intervals_for_timing_rule(self, min_check_in, max_check_out, attendances, schedules_intervals_by_employee):

        def _fill_overtime(employees, rules, intervals, attendances_intervals):
            if not intervals:
                return
            for employee in employees:
                intersetion_interval_for_attendance = attendances_intervals[employee] & intervals[employee]
                overtime_interval_list = defaultdict(list)
                for (start, stop, attendance) in intersetion_interval_for_attendance:
                    overtime_interval_list[attendance].append((start, stop, rules))
                for attendance, attendance_intervals_list in overtime_interval_list.items():
                    overtime_by_employee_by_attendance[employee][attendance] |= Intervals(attendance_intervals_list)

        def _build_day_rule_intervals(employees, rule, intervals):
            timing_intervals_by_employee = defaultdict(Intervals)
            start = min(rule.timing_start, rule.timing_stop)
            stop = max(rule.timing_start, rule.timing_stop)
            for employee in employees:
                for interval in intervals[employee]:
                    start_datetime = datetime.combine(interval[0].date(), float_to_time(start))
                    stop_datetime = datetime.combine(interval[0].date(), float_to_time(stop))
                    timing_intervals = Intervals([(start_datetime, stop_datetime, self.env['resource.calendar'])])
                    if rule.timing_start > rule.timing_stop:
                        day_start = datetime.combine(interval[0].date(), datetime.min.time())
                        day_end = datetime.combine(interval[0].date(), datetime.max.time())
                        timing_intervals = Intervals([
                            (i_start, i_stop, self.env['resource.calendar'])
                        for i_start, i_stop in invert_intervals([(start_datetime, stop_datetime)], day_start, day_end)])
                    timing_intervals_by_employee[employee] |= timing_intervals
            return timing_intervals_by_employee

        employees = attendances.employee_id
        intervals_by_timing_type = self._get_rules_intervals_by_timing_type(
            min_check_in,
            max_check_out,
            employees,
            schedules_intervals_by_employee
        )
        attendances_intervals_by_employee = defaultdict()
        overtime_by_employee_by_attendance = defaultdict(lambda: defaultdict(Intervals))

        attendances_by_employee = attendances.grouped('employee_id')
        for employee, emp_attendance in attendances_by_employee.items():
            attendances_intervals_by_employee[employee] = Intervals([
                (*(attendance._get_localized_times()), attendance)
            for attendance in emp_attendance], keep_distinct=True)

        for timing_type, rules in self.grouped('timing_type').items():
            if timing_type == 'leave':
                _fill_overtime(employees, rules, intervals_by_timing_type['leave'], attendances_intervals_by_employee)

            elif timing_type == 'schedule':
                for calendar, rules in rules.grouped('resource_calendar_id').items():
                    outside_calendar_intervals = intervals_by_timing_type['schedule'][calendar.id]
                    _fill_overtime(employees, rules, outside_calendar_intervals, attendances_intervals_by_employee)
            else:
                for rule in rules:
                    timing_intervals_by_employee = _build_day_rule_intervals(employees, rule, intervals_by_timing_type[timing_type])
                    _fill_overtime(employees, rule, timing_intervals_by_employee, attendances_intervals_by_employee)
        return overtime_by_employee_by_attendance

    def _get_overtime_undertime_intervals_by_employee_by_attendance(self, min_check_in, max_check_out, attendances, schedules_intervals_by_employee):

        def _merge_overtime_dict(d1, d2):
            for employee, overtime_interval_list in d2.items():
                for attendance, overtime_list in overtime_interval_list.items():
                    d1[employee][attendance].extend(overtime_list)

        overtime_by_employee_by_attendance = defaultdict(lambda: defaultdict(list))
        undertime_by_employee_by_attendance = defaultdict(lambda: defaultdict(list))

        quantity_rules = self.filtered_domain([('base_off', '=', 'quantity')])
        if quantity_rules:
            attendances_by_periods_by_employee = attendances._get_attendance_by_periods_by_employee()
            quantity_rule_by_periods = quantity_rules.grouped('quantity_period')
            for period, rules in quantity_rule_by_periods.items():
                quantity_overtime_by_employee_by_attendance, quantity_undertime_by_employee_by_attendance = rules._get_all_overtime_undertime_intervals_for_quantity_rule(attendances_by_periods_by_employee[period], schedules_intervals_by_employee)
                _merge_overtime_dict(overtime_by_employee_by_attendance, quantity_overtime_by_employee_by_attendance)
                _merge_overtime_dict(undertime_by_employee_by_attendance, quantity_undertime_by_employee_by_attendance)

        timing_rules = (self - quantity_rules)
        if not timing_rules:
            return overtime_by_employee_by_attendance, undertime_by_employee_by_attendance

        _merge_overtime_dict(
            overtime_by_employee_by_attendance,
            timing_rules._get_all_overtime_intervals_for_timing_rule(
                min_check_in,
                max_check_out,
                attendances,
                schedules_intervals_by_employee
            )
        )
        return overtime_by_employee_by_attendance, undertime_by_employee_by_attendance

    def _generate_overtime_vals(self, min_check_in, max_check_out, attendances, schedules_intervals_by_employee):
        vals = []

        def _add_overtime_val(attendance, duration_by_day_by_rules):
            for day, duration_by_rules in duration_by_day_by_rules.items():
                for rules, duration in duration_by_rules.items():
                    vals.append({
                        'time_start': attendance.check_in,
                        'time_stop': attendance.check_out,
                        'duration': round(duration, 2),
                        'employee_id': employee.id,
                        'date': day,
                        'rule_ids': rules.ids,
                        **rules._extra_overtime_vals(),
                    })

        overtimes, undertimes = self._get_overtime_undertime_intervals_by_employee_by_attendance(min_check_in, max_check_out, attendances, schedules_intervals_by_employee)
        for employee, intervals_by_attendance in overtimes.items():
            tz = ZoneInfo(employee._get_tz())
            for attendance, intervals in intervals_by_attendance.items():
                duration_by_day_by_rules = defaultdict(lambda: defaultdict(float))
                record_overlap_intervals = _record_overlap_intervals(intervals)
                for start, stop, rules in record_overlap_intervals:
                    date = start.astimezone(tz).date()
                    duration_by_day_by_rules[date][rules] += (stop - start).total_seconds() / 3600
                _add_overtime_val(attendance, duration_by_day_by_rules)

        for employee, intervals_by_attendance in undertimes.items():
            tz = ZoneInfo(employee._get_tz())
            for attendance, intervals in intervals_by_attendance.items():
                duration_by_day_by_rules = defaultdict(lambda: defaultdict(float))
                for duration, rules in intervals:
                    date = attendance.check_in.astimezone(tz).date()
                    duration_by_day_by_rules[date][rules] += duration
                _add_overtime_val(attendance, duration_by_day_by_rules)
        return vals

    def _extra_overtime_vals(self):
        paid_rules = self.filtered('paid')
        if not paid_rules:
            return {'amount_rate': 0.0}

        max_rate_rule = max(paid_rules, key=lambda r: (r.amount_rate, r.sequence))
        if self.ruleset_id.rate_combination_mode == 'max':
            combined_rate = max_rate_rule.amount_rate
        if self.ruleset_id.rate_combination_mode == 'sum':
            combined_rate = sum((r.amount_rate - 1. for r in paid_rules), start=1.)

        return {
            'amount_rate': combined_rate,
        }

    def _compute_information_display(self):
        timing_types = dict(self._fields['timing_type'].selection)
        for rule in self:
            if rule.base_off == 'quantity':
                if rule.expected_hours_from_contract:
                    rule.information_display = self.env._("From Employee")
                    continue
                rule.information_display = self.env._(
                    "%(nb_hours)d h / %(period)s",
                    nb_hours=rule.expected_hours,
                    period={
                        'day': self.env._('day'),
                        'week': self.env._('week'),
                    }[rule.quantity_period],
                )
            else:
                if rule.timing_type == 'schedule':
                    rule.information_display = self.env._(
                        "Outside Schedule: %(schedule_name)s",
                        schedule_name=rule.resource_calendar_id.name,
                    )
                    continue
                rule.information_display = timing_types[rule.timing_type]
