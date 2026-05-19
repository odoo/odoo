# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from ast import literal_eval
from odoo.tools.date_utils import float_to_time, sum_intervals
from odoo.tools.float_utils import float_compare
from odoo.tools.intervals import Intervals, _boundaries, invert_intervals


def _record_overlap_intervals(intervals):
    """Split overlapping rule intervals so each slice carries exactly its active rule set."""
    boundaries = sorted(_boundaries(intervals, 'start', 'stop'))
    counts = {}
    interval_vals = []
    ids = set()
    start = None
    for (time_pt, flag, records) in boundaries:
        for record in records:
            if (new_count := counts.get(record.id, 0) + {'start': 1, 'stop': -1}[flag]):
                counts[record.id] = new_count
            else:
                del counts[record.id]
        new_ids = set(counts.keys())
        if ids != new_ids:
            if ids and start is not None:
                interval_vals.append((start, time_pt, records.browse(ids)))
            if new_ids:
                start = time_pt
        ids = new_ids
    return Intervals(interval_vals, keep_distinct=True)


def _naivify(intervals):
    """Strip tzinfo from an interval iterable, returning a new Intervals object."""
    return Intervals([(s.replace(tzinfo=None), e.replace(tzinfo=None), r) for s, e, r in intervals])


def _trim_hours_from_start(intervals, hours):
    """Remove `hours` worth of time from the beginning of an interval list."""
    remaining = hours
    result = []
    for s, e, r in intervals:
        if remaining <= 0:
            result.append((s, e, r))
            continue
        slot = (e - s).total_seconds() / 3600
        if slot <= remaining:
            remaining -= slot
        else:
            result.append((s + timedelta(hours=remaining), e, r))
            remaining = 0
    return result


class HrTimeRule(models.Model):
    _name = 'hr.time.rule'
    _description = "Time Rule"
    _order = 'sequence, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    country_id = fields.Many2one('res.country')
    company_id = fields.Many2one('res.company')
    employee_domain = fields.Char(string="Employees", default='[]')

    threshold_operator = fields.Selection([
        ('exceed', 'Exceed'),
        ('less_than', 'Less than'),
    ], default='exceed', required=True)

    working_hours_mode = fields.Selection([
        ('schedule_day', 'the daily schedule'),
        ('schedule_week', 'the weekly schedule'),
        ('day', 'per day'),
        ('week', 'per week'),
    ], required=True, default='schedule_day', string="Working Hours Mode")

    calendar_source = fields.Selection([
        ('employee', 'Employee Schedule'),
        ('reference', 'Reference Schedule'),
    ], string="Calendar Source",
        help="Which schedule to use as the expected-hours baseline.",
        compute='_compute_calendar_source',
        store=True,
        readonly=False,
    )
    resource_calendar_id = fields.Many2one('resource.calendar', string="Schedule")
    expected_hours = fields.Float(
        string="Usual work hours",
        compute='_compute_expected_hours',
        store=True,
        readonly=False,
    )
    quantity_period = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
    ], compute='_compute_quantity_period', store=True)

    week_start = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string="Week Starts On", default='0')

    apply_monday = fields.Boolean(default=True)
    apply_tuesday = fields.Boolean(default=True)
    apply_wednesday = fields.Boolean(default=True)
    apply_thursday = fields.Boolean(default=True)
    apply_friday = fields.Boolean(default=True)
    apply_saturday = fields.Boolean(default=True)
    apply_sunday = fields.Boolean(default=True)
    apply_on_public_holidays = fields.Boolean(default=True)

    timing_start = fields.Float("From", default=0)
    timing_stop = fields.Float("To", default=24)

    employee_tolerance = fields.Float()
    employer_tolerance = fields.Float()

    condition_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type',
        'hr_time_rule_condition_work_entry_type_rel',
        string="Time Type",
        required=True,
        domain="[('id', 'in', country_work_entry_type_ids)]",
        help="Only fire this rule for leaves of these types.",
    )

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type',
        string="Set Excess to",
        domain="[('id', 'in', country_work_entry_type_ids), ('requires_allocation', '=', False)]",
    )
    country_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type',
        'hr_time_rule_allowed_work_entry_type_rel',
        compute='_compute_country_work_entry_type_ids',
    )
    amount_rate = fields.Float(
        "Salary Rate",
        compute='_compute_amount_rate',
        store=True,
        readonly=False,
    )

    leave_compensation_rate = fields.Float("Allocate %", default=0.0)
    allocation_type_id = fields.Many2one(
        'hr.work.entry.type',
        string="Allocate to",
        domain="[('requires_allocation', '=', True), ('id', 'in', country_work_entry_type_ids)]",
    )

    _timing_start_is_hour = models.Constraint(
        'CHECK(0 <= timing_start AND timing_start < 24)',
        "Timing Start is an hour of the day",
    )
    _timing_stop_is_hour = models.Constraint(
        'CHECK(0 <= timing_stop AND timing_stop <= 24)',
        "Timing Stop is an hour of the day",
    )
    _timing_start_less_than_timing_stop = models.Constraint(
        'CHECK(timing_start < timing_stop)',
        "Timing Start < Timing Stop",
    )
    _at_least_one_day = models.Constraint(
        'CHECK(apply_monday OR apply_tuesday OR apply_wednesday OR apply_thursday '
        'OR apply_friday OR apply_saturday OR apply_sunday OR apply_on_public_holidays)',
        "A time rule must apply on at least one day or on public holidays.",
    )

    @api.constrains('country_id', 'company_id')
    def _check_company_country(self):
        for rule in self:
            if rule.country_id and rule.company_id and rule.company_id.country_id != rule.country_id:
                raise ValidationError(self.env._(
                    "Rule '%(name)s': the company country (%(company_country)s) does not match the rule country (%(country)s).",
                    name=rule.name,
                    company_country=rule.company_id.country_id.name,
                    country=rule.country_id.name,
                ))

    @api.constrains('expected_hours', 'calendar_source', 'quantity_period')
    def _check_quantity_condition(self):
        for rule in self:
            if not (rule.calendar_source or rule.expected_hours):
                continue
            if not rule.calendar_source and not rule.expected_hours:
                raise ValidationError(self.env._(
                    "Rule '%(name)s': set either a calendar source or a fixed number of hours.",
                    name=rule.name,
                ))
            if not rule.quantity_period:
                raise ValidationError(self.env._(
                    "Rule '%(name)s': a working-hours condition requires a period (day or week).",
                    name=rule.name,
                ))

    @api.depends('country_id', 'company_id')
    def _compute_country_work_entry_type_ids(self):
        for rule in self:
            country = rule.country_id or rule.company_id.country_id or self.env.company.country_id
            if not country or not self.env['hr.work.entry.type'].search_count([('country_id', '=', country.id)], limit=1):
                domain = [('country_id', '=', False)]
            else:
                domain = [('country_id', '=', country.id)]
            rule.country_work_entry_type_ids = self.env['hr.work.entry.type'].search(domain)

    @api.depends('work_entry_type_id.amount_rate')
    def _compute_amount_rate(self):
        for rule in self:
            rule.amount_rate = rule.work_entry_type_id.amount_rate if rule.work_entry_type_id else 1.0

    @api.depends('working_hours_mode')
    def _compute_calendar_source(self):
        for rule in self:
            if rule.working_hours_mode in ('schedule_day', 'schedule_week'):
                if not rule.calendar_source:
                    rule.calendar_source = 'employee'
            else:
                rule.calendar_source = False

    @api.depends('working_hours_mode')
    def _compute_quantity_period(self):
        for rule in self:
            mode = rule.working_hours_mode
            if mode in ('schedule_day', 'day'):
                rule.quantity_period = 'day'
            elif mode in ('schedule_week', 'week'):
                rule.quantity_period = 'week'
            else:
                rule.quantity_period = False

    @api.depends('working_hours_mode')
    def _compute_expected_hours(self):
        for rule in self:
            if rule.working_hours_mode in ('schedule_day', 'schedule_week'):
                rule.expected_hours = 0.0

    def _get_applicable_employees(self, employees):
        self.ensure_one()
        if self.company_id:
            employees = employees.filtered(lambda e: e.company_id == self.company_id)
        if not employees:
            return employees
        if not self.employee_domain or self.employee_domain == '[]':
            return employees
        try:
            domain = literal_eval(self.employee_domain)
        except Exception:  # noqa: BLE001
            return employees
        return employees.sudo().filtered_domain(domain)

    def _weekday_flags(self):
        self.ensure_one()
        return [
            self.apply_monday, self.apply_tuesday, self.apply_wednesday,
            self.apply_thursday, self.apply_friday, self.apply_saturday, self.apply_sunday,
        ]

    def _get_schedule_calendar(self):
        """Return the effective reference calendar for this rule, or False if employee-based."""
        self.ensure_one()
        if self.calendar_source != 'reference':
            return self.env['resource.calendar']
        return (
            self.resource_calendar_id
            or self.company_id.resource_calendar_id
            or self.env.company.resource_calendar_id
        )

    def _build_work_intervals_by_calendar(self, employees, start_dt, end_dt):
        by_calendar = {}
        if self.filtered(lambda r: r.calendar_source != 'reference'):
            by_calendar[False] = self._get_work_intervals(employees, start_dt, end_dt)
        for rule in self.filtered(lambda r: r.calendar_source == 'reference'):
            cal = rule._get_schedule_calendar()
            if cal.id not in by_calendar:
                by_calendar[cal.id] = rule._get_work_intervals(employees, start_dt, end_dt, schedule_calendar=cal)
        return by_calendar

    def _get_work_intervals(self, employees, start_dt, end_dt, schedule_calendar=None):
        version_periods_by_employee = employees.sudo()._get_version_periods(
            start_dt.date(), end_dt.date(),
        )
        result = {
            'schedule':       defaultdict(Intervals),
            'leave':          defaultdict(Intervals),
            'public_leave':   defaultdict(Intervals),
            'fully_flexible': defaultdict(Intervals),
        }
        empty_resource = self.env['resource.resource']
        sched_cache = {}

        for emp, periods in version_periods_by_employee.items():
            tz = ZoneInfo(emp.tz or 'UTC')
            rid = emp.resource_id.id
            emp_resources_per_tz = {tz: emp.resource_id}

            for p_start, p_stop, version in periods:
                p_dt_start = datetime.combine(p_start, time.min, tzinfo=UTC)
                p_dt_end = datetime.combine(p_stop, time.max, tzinfo=UTC)
                period = Intervals([(p_dt_start.replace(tzinfo=None), p_dt_end.replace(tzinfo=None), version)])

                if version.is_fully_flexible:
                    result['fully_flexible'][emp] |= period
                    continue

                sched_cal = schedule_calendar or version.resource_calendar_id
                leave_cal = version.resource_calendar_id

                key = (sched_cal.id, tz, p_dt_start, p_dt_end)
                if key not in sched_cache:
                    tz_empty = {tz: empty_resource}
                    att_batch = sched_cal._attendance_intervals_batch(p_dt_start, p_dt_end, resources_per_tz=tz_empty)
                    ph_batch = sched_cal._leave_intervals_batch(
                        p_dt_start, p_dt_end, resources_per_tz=tz_empty,
                        domain=[('resource_id', '=', False)],
                    )
                    sched_cache[key] = (
                        _naivify(att_batch.get(False, [])),
                        _naivify(ph_batch.get(False, [])),
                    )
                att_intervals, ph_intervals = sched_cache[key]
                result['schedule'][emp] |= att_intervals & period
                result['public_leave'][emp] |= ph_intervals & period

                leave_batch = leave_cal._leave_intervals_batch(
                    p_dt_start, p_dt_end, resources_per_tz=emp_resources_per_tz,
                    domain=[('resource_id', '!=', False), ('count_as', '=', 'absence')],
                )
                result['leave'][emp] |= _naivify(leave_batch.get(rid, [])) & period

        return result

    def _dates_to_day_intervals(self, intervals):
        dates = set()
        for interval in intervals:
            start_dt = interval[0]
            if start_dt.time() == datetime.max.time():
                start_dt += relativedelta(days=1)
            start_day = start_dt.date()
            stop_dt = interval[1]
            if stop_dt.time() == datetime.min.time():
                stop_dt -= relativedelta(days=1)
            stop_day = stop_dt.date()
            if stop_day < start_day:
                continue
            for day in rrule(
                freq=DAILY,
                dtstart=datetime.combine(start_day, datetime.min.time()),
                until=datetime.combine(stop_day, datetime.max.time()),
            ):
                dates.add(day.date())
        return Intervals([
            (
                datetime.combine(date, datetime.min.time()),
                datetime.combine(date, datetime.max.time()),
                self.env['resource.calendar'],
            )
            for date in dates
        ], keep_distinct=True)

    def _build_hour_window_intervals(self, employees, day_intervals_by_employee):
        self.ensure_one()
        result = defaultdict(Intervals)
        window_start = min(self.timing_start, self.timing_stop)
        window_stop = max(self.timing_start, self.timing_stop)
        for employee in employees:
            for interval in day_intervals_by_employee[employee]:
                day = interval[0].date()
                start_dt = datetime.combine(day, float_to_time(window_start))
                stop_dt = datetime.combine(day, float_to_time(window_stop))
                if self.timing_start > self.timing_stop:
                    day_start = datetime.combine(day, datetime.min.time())
                    day_end = datetime.combine(day, datetime.max.time())
                    window = Intervals([
                        (i_start, i_stop, self.env['resource.calendar'])
                        for i_start, i_stop in invert_intervals([(start_dt, stop_dt)], day_start, day_end)
                    ])
                else:
                    window = Intervals([(start_dt, stop_dt, self.env['resource.calendar'])])
                result[employee] |= window
        return result

    def _build_rule_day_intervals(self, min_date, max_date, employees, work_intervals_by_type):
        self.ensure_one()
        weekday_flags = self._weekday_flags()
        all_days = [
            day.date()
            for day in rrule(
                freq=DAILY,
                dtstart=datetime.combine(min_date, datetime.min.time()),
                until=datetime.combine(max_date, datetime.max.time()),
            )
            if weekday_flags[day.weekday()]
        ]
        if not all_days and not self.apply_on_public_holidays:
            return {emp: Intervals() for emp in employees}
        base_intervals = Intervals([
            (
                datetime.combine(d, datetime.min.time()),
                datetime.combine(d, datetime.max.time()),
                self.env['resource.calendar'],
            )
            for d in all_days
        ])
        result = {}
        for employee in employees:
            day_intervals = base_intervals
            public_leave = work_intervals_by_type['public_leave'][employee]
            ph_days = self._dates_to_day_intervals(public_leave)
            if self.apply_on_public_holidays:
                day_intervals = day_intervals | ph_days
            else:
                day_intervals = day_intervals - ph_days
            result[employee] = self._build_hour_window_intervals(
                [employee], {employee: day_intervals},
            )[employee]
        return result

    def _get_localized_leave_interval(self, leave):
        tz = ZoneInfo(leave.employee_id.sudo()._get_tz())
        start = leave.date_from.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        stop = leave.date_to.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        return start, stop

    def _evaluate_period(self, start, stop, leave_intervals, schedule):
        self.ensure_one()
        period_window = Intervals([(start, stop, self.env['resource.calendar'])])
        leaves = self.env['hr.leave']
        intervals_by_leave = defaultdict(Intervals)

        for l_start, l_stop, leave in leave_intervals:
            leaves |= leave
            intervals_by_leave[leave] |= (
                Intervals([(l_start, l_stop, self.env['resource.calendar'])]) & period_window
            )

        if self.calendar_source:
            expected_duration = sum_intervals(schedule & period_window)
        else:
            expected_duration = self.expected_hours

        total_worked = Intervals()
        for lv_intervals in intervals_by_leave.values():
            total_worked |= lv_intervals
        excess_amount = sum_intervals(total_worked) - expected_duration

        if self.threshold_operator == 'less_than':
            deficit_amount = -excess_amount
            if float_compare(deficit_amount, self.employee_tolerance, 5) != 1:
                return {}, {}
            last_leave = sorted(intervals_by_leave.keys(), key=lambda lv: lv.date_to)[-1]
            if self.calendar_source:
                gap = list((schedule & period_window) - total_worked)
                # hours worked outside the schedule reduce the deficit from its start.
                extra_outside = sum_intervals(total_worked) - sum_intervals(total_worked & schedule & period_window)
                if extra_outside > 0:
                    gap = _trim_hours_from_start(gap, extra_outside)
                return {}, {last_leave: [(s, e, self) for s, e, _ in gap]}
            else:
                return {}, {last_leave: [(stop - timedelta(hours=deficit_amount), stop, self)]}

        if float_compare(excess_amount, self.employer_tolerance, 5) != 1:
            return {}, {}

        excess_by_leave = defaultdict(list)
        remaining_expected = expected_duration
        remaining_excess = excess_amount
        for leave in leaves.sorted('date_from'):
            for l_start, l_stop, _ in intervals_by_leave[leave]:
                interval_duration = (l_stop - l_start).total_seconds() / 3600
                if remaining_expected >= interval_duration:
                    remaining_expected -= interval_duration
                    continue
                excess_duration = interval_duration - remaining_expected if remaining_expected else interval_duration
                excess_start = l_stop - timedelta(hours=excess_duration)
                remaining_expected = 0
                excess_by_leave[leave].append((excess_start, l_stop, self))
                remaining_excess -= excess_duration
                if remaining_excess <= 0:
                    return excess_by_leave, {}
        return excess_by_leave, {}

    def _evaluate_rules(self, leaves, start_dt, end_dt):
        excess = defaultdict(lambda: defaultdict(list))
        deficit = defaultdict(lambda: defaultdict(list))

        if not leaves:
            return excess, deficit

        work_intervals_by_calendar = self._build_work_intervals_by_calendar(leaves.employee_id, start_dt, end_dt)
        min_date = min(lv.date_from for lv in leaves).date()
        max_date = max(lv.date_to for lv in leaves).date()

        leave_intervals_by_employee = defaultdict(list)
        for leave in leaves.sorted('date_from'):
            start_local, stop_local = self._get_localized_leave_interval(leave)
            leave_intervals_by_employee[leave.employee_id].append((start_local, stop_local, leave))

        employee = leaves.employee_id
        for rule in self:
            work_intervals = work_intervals_by_calendar[rule._get_schedule_calendar().id or False]
            rule_intervals = rule._build_rule_day_intervals(min_date, max_date, employee, work_intervals)
            has_threshold = bool(rule.calendar_source or rule.expected_hours)

            emp_raw = [
                (s, e, lv) for s, e, lv in leave_intervals_by_employee[employee]
                if lv.work_entry_type_id in rule.condition_work_entry_type_ids
            ]
            if not emp_raw:
                continue
            clipped = Intervals(emp_raw, keep_distinct=True) & rule_intervals[employee]
            if not clipped:
                continue

            if not has_threshold:
                by_leave = defaultdict(list)
                for start, stop, leave in clipped:
                    by_leave[leave].append((start, stop, rule))
                for leave, items in by_leave.items():
                    excess[employee][leave].extend(items)
            else:
                schedule = work_intervals['schedule'][employee] - work_intervals['leave'][employee]
                fully_flex = work_intervals['fully_flexible'][employee]
                period = rule.quantity_period or 'day'

                by_period = defaultdict(list)
                for start, stop, leave in clipped:
                    day = start.date()
                    if period == 'week':
                        week_start = int(rule.week_start or '0')
                        end_weekday = (week_start - 1) % 7
                        days_to_end = (end_weekday - day.weekday()) % 7
                        period_key = day + relativedelta(days=days_to_end)
                    else:
                        period_key = day
                    by_period[period_key].append((start, stop, leave))

                for period_date, period_items in sorted(by_period.items()):
                    period_stop = datetime.combine(period_date, datetime.max.time())
                    period_start = (
                        datetime.combine(period_date, datetime.min.time()) - relativedelta(days=6)
                        if period == 'week' else
                        datetime.combine(period_date, datetime.min.time())
                    )
                    period_window = Intervals([(period_start, period_stop, self.env['resource.calendar'])])
                    if not (period_window - fully_flex):
                        continue
                    schedule_in_window = schedule & rule_intervals[employee] & period_window
                    ex, df = rule._evaluate_period(period_start, period_stop, period_items, schedule_in_window)
                    for lv, items in ex.items():
                        excess[employee][lv].extend(items)
                    for lv, items in df.items():
                        deficit[employee][lv].extend(items)

        return excess, deficit

    def _get_remainder_leave_vals(self, employee, source_leave, date_from, date_to):
        return {
            'employee_id': employee.id,
            'work_entry_type_id': source_leave.work_entry_type_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': date_from.date(),
            'request_date_to': date_to.date(),
            'source_leave_id': source_leave.id,
            'state': 'validate',
        }

    def _get_output_leave_vals(self, employee, rule, date_from, date_to, source_leave, all_rules=None):
        return {
            'employee_id': employee.id,
            'work_entry_type_id': rule.work_entry_type_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': date_from.date(),
            'request_date_to': date_to.date(),
            'time_rule_id': rule.id,
            'source_leave_id': source_leave.id,
            'state': 'validate',
        }

    def _get_output_leave_merge_key(self, all_rules):
        """Hashable key controlling when consecutive excess slices are merged into one leave.

        Override to add extra discriminators (e.g. premium pay rule sets in Belgium).
        `self` is the effective (lowest-sequence) rule; `all_rules` is the full active set.
        """
        return self

    def _apply_output(self, excess, deficit):
        Leave = self.env['hr.leave'].sudo()
        auto_ctx = dict(
            skip_time_rules=True,
            leave_fast_create=True,
            leave_skip_date_check=True,
            leave_skip_state_check=True,
            tracking_disable=True,
            mail_activity_automation_skip=True,
        )

        for employee, by_leave in deficit.items():
            tz = ZoneInfo(employee._get_tz())
            for source_leave, intervals in by_leave.items():
                # among deficit rules competing for the same (period_type, period),
                # only the lowest-sequence rule produces output.
                by_period = defaultdict(list)
                for start, stop, rule in intervals:
                    if rule.quantity_period == 'week':
                        ws = int(rule.week_start or '0')
                        days_to_end = ((ws - 1) % 7 - start.weekday()) % 7
                        pkey = ('week', start.date() + timedelta(days=days_to_end))
                    else:
                        pkey = ('day', start.date())
                    by_period[pkey].append((start, stop, rule))

                winning_intervals = []
                for pivs in by_period.values():
                    all_period_rules = self.browse([r.id for _, _, r in pivs])
                    min_seq = min(r.sequence for r in all_period_rules)
                    for s, e, r in pivs:
                        if r.sequence == min_seq:
                            winning_intervals.append((s, e, r, all_period_rules))

                for start_local, stop_local, rule, all_rules in winning_intervals:
                    if not rule.work_entry_type_id:
                        continue
                    date_from = start_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    date_to = stop_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    Leave.with_context(**auto_ctx).create(
                        self._get_output_leave_vals(employee, rule, date_from, date_to, source_leave, all_rules=all_rules)
                    )

                    if rule.leave_compensation_rate > 0 and rule.allocation_type_id:
                        deficit_hours = (date_to - date_from).total_seconds() / 3600
                        deduct_days = deficit_hours * rule.leave_compensation_rate / 100
                        allocation = self.env['hr.leave.allocation'].sudo().search([
                            ('employee_id', '=', employee.id),
                            ('work_entry_type_id', '=', rule.allocation_type_id.id),
                            ('state', '=', 'validate'),
                        ], limit=1)
                        if allocation:
                            allocation.number_of_days = max(0, allocation.number_of_days - deduct_days)

        for employee, by_leave in excess.items():
            tz = ZoneInfo(employee._get_tz())
            for source_leave, intervals in by_leave.items():
                slices = list(_record_overlap_intervals(intervals))
                output_slices = [
                    (start, stop, rules)
                    for start, stop, rules in slices
                    if stop > start and rules.filtered('work_entry_type_id')
                ]
                if not output_slices:
                    continue

                # split source around outputs; remainder[0] stays as source, rest become new leaves
                src_start = source_leave.date_from.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
                src_stop = source_leave.date_to.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
                src_iv = Intervals([(src_start, src_stop, self.env['resource.calendar'])])
                out_iv = Intervals(
                    [(s, e, self.env['resource.calendar']) for s, e, _ in output_slices],
                    keep_distinct=True,
                )
                remainder = list(src_iv - out_iv)

                if remainder:
                    first_start, first_stop, _ = remainder[0]
                    first_date_from = first_start.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    first_date_to = first_stop.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    source_leave.with_context(**auto_ctx).write({
                        'date_from': first_date_from,
                        'date_to': first_date_to,
                        'request_date_from': first_date_from.date(),
                        'request_date_to': first_date_to.date(),
                    })
                    for seg_start, seg_stop, _ in remainder[1:]:
                        seg_date_from = seg_start.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        seg_date_to = seg_stop.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        Leave.with_context(**auto_ctx).create(
                            self._get_remainder_leave_vals(employee, source_leave, seg_date_from, seg_date_to)
                        )
                else:
                    # zero out source so no work entry is generated for it
                    source_leave.with_context(**auto_ctx).write({
                        'date_to': source_leave.date_from,
                        'request_date_to': source_leave.date_from.date(),
                    })

                for start_local, stop_local, rules in output_slices:
                    alloc_rules = rules.filtered(
                        lambda r: r.leave_compensation_rate > 0 and r.allocation_type_id
                    )
                    for alloc_rule in alloc_rules:
                        excess_hours = (stop_local - start_local).total_seconds() / 3600
                        alloc_days = excess_hours * alloc_rule.leave_compensation_rate / 100
                        if alloc_days <= 0:
                            continue
                        allocation = self.env['hr.leave.allocation'].sudo().search([
                            ('employee_id', '=', employee.id),
                            ('work_entry_type_id', '=', alloc_rule.allocation_type_id.id),
                            ('state', '=', 'validate'),
                        ], limit=1)
                        if allocation:
                            allocation.number_of_days += alloc_days
                        else:
                            allocation = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True).create({
                                'employee_id': employee.id,
                                'work_entry_type_id': alloc_rule.allocation_type_id.id,
                                'number_of_days': alloc_days,
                                'state': 'confirm',
                            })
                            allocation.action_approve()

                # merged_slices entries: [start, stop, all_rules, effective_rule, merge_key]
                merged_slices = []
                for start, stop, rules in output_slices:
                    effective = rules.sorted('sequence').filtered('work_entry_type_id')[:1]
                    merge_key = effective._get_output_leave_merge_key(rules)
                    if merged_slices and merged_slices[-1][1] == start and merged_slices[-1][4] == merge_key:
                        merged_slices[-1][1] = stop
                        merged_slices[-1][2] |= rules
                    else:
                        merged_slices.append([start, stop, rules, effective, merge_key])

                for start_local, stop_local, all_rules, rule, _merge_key in merged_slices:
                    date_from = start_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    date_to = stop_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    Leave.with_context(**auto_ctx).create(
                        self._get_output_leave_vals(employee, rule, date_from, date_to, source_leave, all_rules=all_rules)
                    )
