# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from ast import literal_eval
from odoo.tools.date_utils import float_to_time, sum_intervals
from odoo.tools.float_utils import float_compare
from odoo.tools.intervals import Intervals, _boundaries, invert_intervals


def resolve_intervals_by_sequence(intervals):
    """For each non-overlapping sub-interval, pick the payload with the lowest sequence.

    intervals: iterable of (start, stop, payload) where payload has a .sequence attribute.
    Zero-duration slices are silently dropped.
    Returns a list of (start, stop, payload) with no overlaps.
    """
    valid = [(s, e, p) for s, e, p in intervals if e > s]
    if not valid:
        return []
    times = sorted({t for s, e, _ in valid for t in (s, e)})
    result = []
    for t0, t1 in pairwise(times):
        best = min(
            (p for s, e, p in valid if s <= t0 and t1 <= e),
            key=lambda r: r.sequence,
            default=None,
        )
        if best:
            result.append((t0, t1, best))
    return result


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


def _split_by_window(intervals, window):
    """Partition pipeline 6-tuples (s, e, wet, pp, src, cls_rule) by a rule window.

    Returns (inside, outside)
    portions that fall within / outside window.
    The window is an Intervals object (sorted, non-overlapping segments).
    """
    inside = []
    outside = []
    win_segs = [(ws, we) for ws, we, _ in window]
    for s, e, w, pp, src, cls_rule in intervals:
        prev = s
        for ws, we in win_segs:
            cs = max(s, ws)
            ce = min(e, we)
            if cs < ce:
                if prev < cs:
                    outside.append((prev, cs, w, pp, src, cls_rule))
                inside.append((cs, ce, w, pp, src, cls_rule))
                prev = ce
        if prev < e:
            outside.append((prev, e, w, pp, src, cls_rule))
    return inside, outside


class HrTimeRule(models.Model):
    _name = 'hr.time.rule'
    _description = "Time Rule"
    _order = 'sequence, id'

    name = fields.Char(required=True)
    description = fields.Text()
    condition_label = fields.Char(compute='_compute_condition_label', string="Condition")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    country_id = fields.Many2one('res.country', compute='_compute_country_id', store=True, readonly=False, index="btree_not_null")
    country_code = fields.Char(related='country_id.code')
    company_id = fields.Many2one('res.company')
    employee_domain = fields.Char(
        string="Employees",
        default='[]',
        help="The rule will automatically apply to all time entries for matching employees.",
    )

    threshold_operator = fields.Selection([
        ('exceed', 'Exceed'),
        ('less_than', 'Less than'),
    ], default='exceed', required=True)

    working_hours_mode = fields.Selection([
        ('schedule_day', 'the daily schedule'),
        ('schedule_week', 'the weekly schedule'),
        ('day', 'per day'),
        ('week', 'per week'),
    ], required=True, default='schedule_day', string="Working Hours Mode",
        help="Define a condition based on the quantity of work made by the employee on a specific period of time.",
    )

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

    apply_monday = fields.Boolean(default=True, help="Define a condition based on the timing of the time entry.")
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
        help="If set, only the selected types will be considered by this rule.",
    )

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type',
        string="Set Excess to",
        domain="[('id', 'in', country_work_entry_type_ids)]",
        help="Define a time type that will be created to count the amount of time in excess or missing.",
        index="btree_not_null",
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

    def copy_data(self, default=None):
        vals_list = super().copy_data(default)
        return [dict(vals, name=self.env._("%s (copy)", rule.name)) for rule, vals in zip(self, vals_list)]

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

    @api.depends('threshold_operator', 'working_hours_mode', 'expected_hours', 'timing_start', 'timing_stop')
    def _compute_condition_label(self):
        def _fmt_hour(h):
            hh, mm = divmod(round(h * 60), 60)
            return f"{hh:02d}:{mm:02d}"

        for rule in self:
            op = '>' if rule.threshold_operator == 'exceed' else '<'
            mode = rule.working_hours_mode
            if mode in ('schedule_day', 'schedule_week'):
                period = 'day' if mode == 'schedule_day' else 'week'
                label = f"{op} schedule/{period}"
            else:
                period = 'day' if mode == 'day' else 'week'
                label = f"{op} {rule.expected_hours:g}h/{period}"
            if rule.timing_start != 0 or rule.timing_stop != 24:
                label += f" {_fmt_hour(rule.timing_start)}-{_fmt_hour(rule.timing_stop)}"
            rule.condition_label = label

    @api.depends('company_id')
    def _compute_country_id(self):
        for rule in self:
            if rule.company_id:
                rule.country_id = rule.company_id.country_id

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
        elif self.country_id:
            employees = employees.filtered(lambda e: e.company_id.country_id == self.country_id)
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
        leave_requests = defaultdict(list)

        for emp, periods in version_periods_by_employee.items():
            tz = ZoneInfo(emp.tz or 'UTC')
            rid = emp.resource_id.id

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

                leave_requests[leave_cal.id, p_dt_start, p_dt_end].append(
                    (emp, rid, tz, leave_cal, period)
                )

        for (_, p_dt_start, p_dt_end), items in leave_requests.items():
            leave_cal = items[0][3]
            resources_per_tz = {}
            for emp, _rid, tz, _, _ in items:
                if tz not in resources_per_tz:
                    resources_per_tz[tz] = emp.resource_id
                else:
                    resources_per_tz[tz] = resources_per_tz[tz] | emp.resource_id
            leave_batch = leave_cal._leave_intervals_batch(
                p_dt_start, p_dt_end, resources_per_tz=resources_per_tz,
                domain=[('resource_id', '!=', False), ('count_as', '=', 'absence')],
            )
            for emp, rid, _, _, period in items:
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

    def _get_record_interval_local(self, record):
        """Return (start_local, stop_local) for a time record in the employee's tz.

        Works for any model that has employee_id, date_from, date_to.
        """
        tz = ZoneInfo(record.employee_id.sudo()._get_tz())
        start = record.date_from.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        stop = record.date_to.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        return start, stop

    def _get_pp_frozenset(self):
        """Return frozenset of premium pay IDs to attach when this rule classifies an interval."""
        self.ensure_one()
        return frozenset()

    def _evaluate_period(self, start, stop, record_intervals, schedule):
        """Evaluate one time period against this rule's threshold.

        record_intervals: list of (start, stop, source) 3-tuples extracted from the
            pipeline for this period.

        Returns (excess_by_source, deficit_by_source) where each value is a list of
        (start, stop, rule, frozenset_pp) 4-tuples.  frozenset_pp is populated by
        _get_pp_frozenset(); Belgium overrides that to return actual salary rule IDs.
        """
        self.ensure_one()
        pp = self._get_pp_frozenset()
        period_window = Intervals([(start, stop, self.env['resource.calendar'])])
        intervals_by_source = defaultdict(Intervals)

        for r_start, r_stop, source in record_intervals:
            intervals_by_source[source] |= (
                Intervals([(r_start, r_stop, self.env['resource.calendar'])]) & period_window
            )

        if self.calendar_source:
            expected_duration = sum_intervals(schedule & period_window)
        else:
            expected_duration = self.expected_hours

        total_worked = Intervals()
        for src_intervals in intervals_by_source.values():
            total_worked |= src_intervals
        excess_amount = sum_intervals(total_worked) - expected_duration

        if self.threshold_operator == 'less_than':
            deficit_amount = -excess_amount
            tolerance = self.employee_tolerance if self.calendar_source else 0
            if float_compare(deficit_amount, tolerance, 5) != 1:
                return {}, {}
            last_source = max(
                intervals_by_source.keys(),
                key=lambda r: max(e for _, e, _ in intervals_by_source[r]),
            )
            if self.calendar_source:
                gap = list((schedule & period_window) - total_worked)
                extra_outside = sum_intervals(total_worked) - sum_intervals(total_worked & schedule & period_window)
                if extra_outside > 0:
                    gap = _trim_hours_from_start(gap, extra_outside)
                return {}, {last_source: [(s, e, self, pp) for s, e, _ in gap]}
            else:
                return {}, {last_source: [(stop - timedelta(hours=deficit_amount), stop, self, pp)]}

        tolerance = self.employer_tolerance if self.calendar_source else 0
        if float_compare(excess_amount, tolerance, 5) != 1:
            return {}, {}

        excess_by_source = defaultdict(list)
        remaining_expected = expected_duration
        remaining_excess = excess_amount
        sorted_sources = sorted(
            intervals_by_source.keys(),
            key=lambda r: min(s for s, _, _ in intervals_by_source[r]),
        )
        for source in sorted_sources:
            for r_start, r_stop, _ in intervals_by_source[source]:
                interval_duration = (r_stop - r_start).total_seconds() / 3600
                if remaining_expected >= interval_duration:
                    remaining_expected -= interval_duration
                    continue
                excess_duration = interval_duration - remaining_expected if remaining_expected else interval_duration
                excess_start = r_stop - timedelta(hours=excess_duration)
                remaining_expected = 0
                excess_by_source[source].append((excess_start, r_stop, self, pp))
                remaining_excess -= excess_duration
                if remaining_excess <= 0:
                    return excess_by_source, {}
        return excess_by_source, {}

    def _evaluate_rules(self, records, start_dt, end_dt):
        """Evaluate all rules sequentially against a recordset of time records.

        Each rule fires in sequence order and sees all current pipeline intervals —
        both original and those classified by prior rules. Returns (excess, deficit)
        keyed by employee then source record, with 4-tuple (s, e, rule, pp) values.
        """
        excess = defaultdict(lambda: defaultdict(list))
        deficit = defaultdict(lambda: defaultdict(list))

        if not records:
            return excess, deficit

        employees = records.employee_id
        work_intervals_by_calendar = self._build_work_intervals_by_calendar(employees, start_dt, end_dt)
        min_date = min(r.date_from for r in records).date()
        max_date = max(r.date_to for r in records).date()

        # pipeline: (start, stop, current_wet, pp, source, classifying_rule)
        # classifying_rule=None means the interval is still in its original state
        pipeline_by_emp = defaultdict(list)
        for record in records.sorted('date_from'):
            start_local, stop_local = self._get_record_interval_local(record)
            pipeline_by_emp[record.employee_id].append(
                (start_local, stop_local, record.work_entry_type_id, frozenset(), record, None)
            )

        for rule in self:
            work_intervals = work_intervals_by_calendar[rule._get_schedule_calendar().id or False]
            rule_window_by_emp = rule._build_rule_day_intervals(min_date, max_date, employees, work_intervals)
            condition_wets = rule.condition_work_entry_type_ids
            has_threshold = bool(rule.calendar_source or rule.expected_hours)

            for employee in rule._get_applicable_employees(employees):
                emp_pipeline = pipeline_by_emp[employee]
                rule_window = rule_window_by_emp[employee]

                # split pipeline into intervals whose current WET matches the rule condition
                matching = [iv for iv in emp_pipeline if iv[2] in condition_wets]
                non_matching = [iv for iv in emp_pipeline if iv[2] not in condition_wets]
                if not matching:
                    continue

                # clip matching intervals to the rule's timing window
                inside, outside = _split_by_window(matching, rule_window)
                if not inside:
                    continue

                if not has_threshold:
                    if not rule.work_entry_type_id:
                        continue
                    rule_pp = rule._get_pp_frozenset()
                    pipeline_by_emp[employee] = non_matching + outside + [
                        (s, e, rule.work_entry_type_id, pp | rule_pp, src, rule)
                        for s, e, _wet, pp, src, _cr in inside
                    ]
                    continue

                schedule = (
                    work_intervals['schedule'][employee]
                    - work_intervals['leave'][employee]
                    - work_intervals['public_leave'][employee]
                )
                fully_flex = work_intervals['fully_flexible'][employee]
                period = rule.quantity_period or 'day'

                by_period = defaultdict(list)
                for s, e, _wet, _pp, src, _cr in inside:
                    day = s.date()
                    if period == 'week':
                        week_start_int = int(rule.week_start or '0')
                        end_weekday = (week_start_int - 1) % 7
                        days_to_end = (end_weekday - day.weekday()) % 7
                        period_key = day + relativedelta(days=days_to_end)
                    else:
                        period_key = day
                    by_period[period_key].append((s, e, src))

                all_excess = defaultdict(list)
                for period_date, period_items in sorted(by_period.items()):
                    period_stop = datetime.combine(period_date, datetime.max.time())
                    period_start = (
                        datetime.combine(period_date, datetime.min.time()) - relativedelta(days=6)
                        if period == 'week' else
                        datetime.combine(period_date, datetime.min.time())
                    )
                    period_window_iv = Intervals([(period_start, period_stop, self.env['resource.calendar'])])
                    if rule.calendar_source and not (period_window_iv - fully_flex):
                        continue
                    schedule_in_window = schedule & rule_window & period_window_iv
                    ex, df = rule._evaluate_period(period_start, period_stop, period_items, schedule_in_window)
                    for source, items in df.items():
                        deficit[employee][source].extend(items)
                    for source, items in ex.items():
                        all_excess[source].extend(items)

                if not all_excess:
                    continue

                # split inside intervals at excess boundaries, reclassifying the excess portions
                new_inside = []
                for iv_start, iv_end, wet, acc_pp, source, cls_rule in inside:
                    if source not in all_excess:
                        new_inside.append((iv_start, iv_end, wet, acc_pp, source, cls_rule))
                        continue
                    cursor = iv_start
                    for exc_start, exc_end, exc_rule, rule_pp in all_excess[source]:
                        clip_start = max(cursor, exc_start)
                        clip_end = min(iv_end, exc_end)
                        if cursor < clip_start:
                            new_inside.append((cursor, clip_start, wet, acc_pp, source, cls_rule))
                        if clip_start < clip_end:
                            new_inside.append((clip_start, clip_end, exc_rule.work_entry_type_id, acc_pp | rule_pp, source, exc_rule))
                        cursor = max(cursor, clip_end)
                    if cursor < iv_end:
                        new_inside.append((cursor, iv_end, wet, acc_pp, source, cls_rule))
                pipeline_by_emp[employee] = non_matching + outside + new_inside

        # extract final excess: pipeline intervals where a rule has classified them
        for employee, emp_pipeline in pipeline_by_emp.items():
            for iv_start, iv_end, _wet, acc_pp, source, cls_rule in emp_pipeline:
                if cls_rule is not None and iv_end > iv_start:
                    excess[employee][source].append((iv_start, iv_end, cls_rule, acc_pp))

        return excess, deficit
