# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict, namedtuple
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
from odoo.tools.intervals import Intervals, invert_intervals

_logger = logging.getLogger(__name__)

# single interval shape used throughout the pipeline, excess, and output stages.
# pp starts empty and is filled in by _resolve_output_intervals; source is the record
# being classified (hr.leave or hr.attendance) and doubles as the excess dict key.
_Iv = namedtuple('_Iv', 'start end wet source rule acc pp',
                 defaults=(None, None, frozenset(), frozenset()))


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


def _to_utc(dt, tz):
    """Convert a naive local datetime to a naive UTC datetime."""
    return dt.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)


def _from_utc(dt, tz):
    """Convert a naive UTC datetime to a naive local datetime."""
    return dt.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)


def _split_by_window(intervals, window):
    """Partition _Iv pipeline intervals by a rule window.

    Returns (inside, outside): portions that fall within / outside window.
    The window is an Intervals object (sorted, non-overlapping segments).
    """
    inside = []
    outside = []
    win_segs = [(ws, we) for ws, we, _ in window]
    for iv in intervals:
        prev = iv.start
        for ws, we in win_segs:
            cs = max(iv.start, ws)
            ce = min(iv.end, we)
            if cs < ce:
                if prev < cs:
                    outside.append(iv._replace(start=prev, end=cs))
                inside.append(iv._replace(start=cs, end=ce))
                prev = ce
        if prev < iv.end:
            outside.append(iv._replace(start=prev, end=iv.end))
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
            country = rule.country_id or rule.company_id.country_id
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
                    # mark the employee as fully flexible for this period
                    result['fully_flexible'][emp] |= period
                    if not schedule_calendar:
                        # no reference calendar provided: the employee's own (absent)
                        # schedule would be the baseline -> nothing to compare against.
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

                if leave_cal:
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
        """Return (start_local, stop_local) for a time record in the employee's tz."""
        tz = ZoneInfo(record.employee_id.sudo()._get_tz())
        start_field = record._time_rule_span_start_field
        end_field = record._time_rule_span_end_field
        start = _from_utc(record[start_field], tz)
        stop = _from_utc(record[end_field], tz)
        return start, stop

    def _get_pp_frozenset(self):
        """Return frozenset of premium pay IDs to attach when this rule classifies an interval."""
        self.ensure_one()
        return frozenset()

    def _get_output_in_place_extra_vals(self, accumulated_pp=frozenset()):
        """Extra write vals when the source record is repurposed in-place as the first output segment.

        Override to propagate fields that _get_output_*_vals sets on newly created records
        but that the in-place write path would otherwise miss (e.g. l10n_be_premium_pay_rule_ids).
        """
        return {}

    def _resolve_output_intervals(self, intervals):
        """Resolve each excess _Iv to its output form.

        Filters zero-duration and unresolvable intervals, computes wet (the effective output WET:
        rule.work_entry_type_id or the source wet) and pp (union of all classifiers' pp frozensets,
        derived from acc | {rule}), then returns the updated _Iv list via _replace.
        Subclasses may merge consecutive slices (e.g. by merge key for leaves).
        """
        result = []
        for iv in sorted(intervals, key=lambda iv: iv.start):
            effective_wet = iv.rule.work_entry_type_id or iv.wet
            if not effective_wet or iv.end <= iv.start:
                continue
            pp = frozenset().union(*(rule._get_pp_frozenset() for rule in iv.acc | {iv.rule}))
            result.append(iv._replace(wet=effective_wet, pp=pp))
        return result

    def _apply_output(self, excess, deficit, active_iv=None):
        """Shared apply-output implementation for both leaves and attendances.

        active_iv: schedule-clipped pipeline intervals per source.
        Returns (new_records, all_source_ids, excess_alloc, deficit_alloc) where
        excess_alloc / deficit_alloc are lists of (employee, rule, hours).
        """
        create_vals = []
        all_source_ids = set()
        dummy = self.env['resource.calendar']
        excess_alloc = []
        deficit_alloc = []

        for employee, by_source in deficit.items():
            tz = ZoneInfo(employee._get_tz())
            for source, intervals in by_source.items():
                all_source_ids.add(source.id)
                # group by period, pick the lowest-sequence rule per period
                by_period = defaultdict(list)
                for iv_start, iv_end, rule in intervals:
                    if not rule.work_entry_type_id or iv_end <= iv_start:
                        continue
                    if rule.quantity_period == 'week':
                        ws = int(rule.week_start or '0')
                        days_to_end = ((ws - 1) % 7 - iv_start.weekday()) % 7
                        period_key = iv_start.date() + timedelta(days=days_to_end)
                    else:
                        period_key = iv_start.date()
                    by_period[period_key].append((iv_start, iv_end, rule))
                for period_key, period_ivs in by_period.items():
                    winning_rule = min(period_ivs, key=lambda t: t[2].sequence)[2]
                    period_end_date = period_key + timedelta(1)
                    period_end = _to_utc(datetime.combine(period_end_date, time.min), tz)
                    for iv_start, iv_end, rule in period_ivs:
                        if rule != winning_rule:
                            continue
                        pp = rule._get_pp_frozenset()
                        df = _to_utc(iv_start, tz)
                        deficit_hours = (iv_end - iv_start).total_seconds() / 3600
                        occupied = source._get_time_rule_deficit_occupied(employee.id, df, period_end)
                        remaining = deficit_hours
                        for slot_s, slot_e, _ in Intervals([(df, period_end, dummy)]) - occupied:
                            if remaining <= 1e-6:
                                break
                            slot_hours = (slot_e - slot_s).total_seconds() / 3600
                            if slot_hours > remaining:
                                slot_e = slot_s + timedelta(hours=remaining)
                            create_vals.append(source._get_time_rule_output_vals(rule, slot_s, slot_e, pp))
                            remaining -= (slot_e - slot_s).total_seconds() / 3600
                        deficit_alloc.append((employee, rule, deficit_hours))

        for employee, by_source in excess.items():
            tz = ZoneInfo(employee._get_tz())
            for source, intervals in by_source.items():
                all_source_ids.add(source.id)

                # credit displaced rules (acc) that had their classification overwritten.
                # they produced no output record but still earn allocation for the hours they claimed.
                for iv in intervals:
                    if iv.end > iv.start:
                        hours = (iv.end - iv.start).total_seconds() / 3600
                        for prev_rule in iv.acc:
                            excess_alloc.append((employee, prev_rule, hours))

                output_intervals = self._resolve_output_intervals(intervals)
                if not output_intervals:
                    continue

                # pp-only rules (no rule WET): all intervals retain the source WET.
                # just accumulate pp across all intervals and write to source, no splitting.
                # still record excess hours so callers with allocation_type_id can allocate them.
                if all(not iv.rule.work_entry_type_id for iv in output_intervals):
                    all_pp = frozenset().union(*(iv.pp for iv in output_intervals))
                    # collect extra_vals from every distinct classifying rule so that
                    # future overrides of _get_output_in_place_extra_vals that inspect
                    # self are all called, not just the first interval's rule.
                    extra_vals = {}
                    for rule in dict.fromkeys(iv.rule for iv in output_intervals):
                        extra_vals |= rule._get_output_in_place_extra_vals(accumulated_pp=all_pp)
                    if extra_vals:
                        source.sudo().with_context(**source._time_rule_write_ctx).write(extra_vals)
                    for iv in output_intervals:
                        excess_alloc.append((employee, iv.rule, (iv.end - iv.start).total_seconds() / 3600))
                    continue

                start_field = source._time_rule_span_start_field
                src_start_local = _from_utc(source[start_field], tz)
                src_stop_local = _from_utc(source[source._time_rule_span_end_field], tz)
                source_wet_id = source.work_entry_type_id.id

                out_union = Intervals([(s, e, dummy) for s, e, *_ in output_intervals], keep_distinct=True)
                src_iv = (
                    active_iv[employee][source]
                    if active_iv and source in active_iv.get(employee, {})
                    else Intervals([(src_start_local, src_stop_local, dummy)])
                )
                remainder_segments = list(src_iv - out_union)

                min_out_start_utc = min(_to_utc(iv.start, tz) for iv in output_intervals)
                src_start_utc = source[start_field]

                if min_out_start_utc <= src_start_utc:
                    first = output_intervals[0]
                    first_end_utc = _to_utc(first.end, tz)
                    extra_vals = first.rule._get_output_in_place_extra_vals(accumulated_pp=first.pp)
                    if not (
                        source.work_entry_type_id == first.wet
                        and source.time_rule_id == first.rule
                        and source[source._time_rule_span_end_field] == first_end_utc
                    ):
                        source.sudo().with_context(**source._time_rule_write_ctx).write({
                            'work_entry_type_id': first.wet.id,
                            'time_rule_id': first.rule.id,
                            **source._get_time_rule_end_write_vals(first_end_utc, first.end),
                            **extra_vals,
                        })
                    elif extra_vals:
                        # main fields already match but pp categories may still need updating
                        source.sudo().with_context(**source._time_rule_write_ctx).write(extra_vals)
                    for seg_s, seg_e, _ in remainder_segments:
                        create_vals.append(source._get_time_rule_remainder_vals(_to_utc(seg_s, tz), _to_utc(seg_e, tz))
                                           | {'work_entry_type_id': source_wet_id})
                    # in-place first interval: count its hours for allocation
                    excess_alloc.append((employee, first.rule, (first.end - first.start).total_seconds() / 3600))
                    subsequent = output_intervals[1:]
                else:
                    min_out_start_local = min(iv.start for iv in output_intervals)
                    source.sudo().with_context(**source._time_rule_write_ctx).write(
                        source._get_time_rule_end_write_vals(min_out_start_utc, min_out_start_local)
                    )
                    for seg_s, seg_e, _ in remainder_segments[1:]:
                        create_vals.append(source._get_time_rule_remainder_vals(_to_utc(seg_s, tz), _to_utc(seg_e, tz))
                                           | {'work_entry_type_id': source_wet_id})
                    subsequent = output_intervals

                for iv in subsequent:
                    create_vals.append(source._get_time_rule_output_vals(iv.rule, _to_utc(iv.start, tz), _to_utc(iv.end, tz), iv.pp))
                    excess_alloc.append((employee, iv.rule, (iv.end - iv.start).total_seconds() / 3600))

        any_source = next(
            (src for by_source in excess.values() for src in by_source),
            next((src for by_source in deficit.values() for src in by_source), None),
        )
        if any_source is None:
            _logger.warning("time rule apply_output: no excess/deficit produced — no records created")
            return None, frozenset(), [], []
        _logger.warning(
            "time rule apply_output: creating %d %s output record(s) for %d source(s)",
            len(create_vals), any_source._name, len(all_source_ids),
        )
        new_records = self.env[any_source._name].sudo().with_context(**any_source._time_rule_write_ctx).create(create_vals)
        return new_records, all_source_ids, excess_alloc, deficit_alloc

    def _evaluate_period(self, start, stop, record_intervals, schedule):
        """Evaluate one time period against this rule's threshold.

        record_intervals: list of (start, stop, source) 3-tuples extracted from the
            pipeline for this period.

        Returns (excess_by_source, deficit_by_source) where each value is a list of
        (start, stop, rule) 3-tuples.  pp is derived lazily from rule._get_pp_frozenset()
        at consumption time.
        """
        self.ensure_one()
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
            tolerance = self.employee_tolerance
            _logger.warning(
                "rule '%s' (id=%d) period %s→%s: worked=%.4fh expected=%.4fh "
                "deficit=%.4fh tolerance=%.4fh → %s",
                self.name, self.id, start.date(), stop.date(),
                sum_intervals(total_worked), expected_duration,
                deficit_amount, tolerance,
                "DEFICIT" if float_compare(deficit_amount, tolerance, 5) == 1 else "below tolerance",
            )
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
                return {}, {last_source: [(s, e, self) for s, e, _ in gap]}
            else:
                gap_iv = period_window - total_worked
                gap = list(gap_iv)
                trim = sum_intervals(gap_iv) - deficit_amount
                if trim > 0:
                    gap = _trim_hours_from_start(gap, trim)
                return {}, {last_source: [(s, e, self) for s, e, _ in gap]}

        tolerance = self.employer_tolerance
        _logger.warning(
            "rule '%s' (id=%d) period %s→%s: worked=%.4fh expected=%.4fh "
            "excess=%.4fh tolerance=%.4fh → %s",
            self.name, self.id, start.date(), stop.date(),
            sum_intervals(total_worked), expected_duration,
            excess_amount, tolerance,
            "EXCESS" if float_compare(excess_amount, tolerance, 5) == 1 else "below tolerance",
        )
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
                excess_by_source[source].append((excess_start, r_stop, self))
                remaining_excess -= excess_duration
                if remaining_excess <= 0:
                    return excess_by_source, {}
        return excess_by_source, {}

    def _evaluate_rules(self, records, start_dt, end_dt):
        """Evaluate all rules sequentially against a recordset of time records.

        Each rule fires in sequence order and sees all current pipeline intervals —
        both original and those classified by prior rules. Returns (excess, deficit, active_iv)
        keyed by employee then source record. excess values are _Iv instances (pp still frozenset();
        filled in by _resolve_output_intervals). deficit values are 3-tuples (s, e, rule).
        active_iv carries the union of pipeline segments per source for remainder computation.
        """
        excess = defaultdict(lambda: defaultdict(list))
        deficit = defaultdict(lambda: defaultdict(list))
        active_iv = defaultdict(lambda: defaultdict(Intervals))

        if not records:
            return excess, deficit, active_iv

        employees = records.employee_id
        applicable_rules = self.filtered(lambda r: bool(r._get_applicable_employees(employees)))
        skipped_rules = self - applicable_rules
        if skipped_rules:
            _logger.warning(
                "time rule evaluate: %d rule(s) not applicable to employees %s: %s",
                len(skipped_rules), employees.mapped('name'), skipped_rules.mapped('name'),
            )
        if not applicable_rules:
            return excess, deficit, active_iv
        _logger.warning(
            "time rule evaluate: %d applicable rule(s) for %d employee(s) on %d source(s)",
            len(applicable_rules), len(employees), len(records),
        )
        work_intervals_by_calendar = applicable_rules._build_work_intervals_by_calendar(employees, start_dt, end_dt)
        start_field = records._time_rule_span_start_field

        # base schedule for schedule-aware interval splitting (e.g. multi-day absence leaves).
        # mirrors _get_durations: by default compute_leaves=True subtracts public holidays,
        # but leave types with include_public_holidays_in_duration=True keep them.
        base_work = work_intervals_by_calendar.get(False) or next(iter(work_intervals_by_calendar.values()), {})
        base_raw_sched = base_work.get('schedule', defaultdict(Intervals))
        base_public_leave = base_work.get('public_leave', defaultdict(Intervals))
        base_sched_no_ph = defaultdict(Intervals)
        for emp in employees:
            base_sched_no_ph[emp] = base_raw_sched[emp] - base_public_leave[emp]

        # pipeline: (start, stop, current_wet, source, classifying_rule, alloc_acc)
        # classifying_rule=None means the interval is still in its original state.
        # alloc_acc is a frozenset of rules that previously classified this interval and were later
        # displaced by a higher-priority rule.  pp and allocation credit for an interval are derived
        # from the union of all rules in alloc_acc plus the current classifying_rule at extraction time.
        pipeline_by_emp = defaultdict(list)
        dummy = self.env['resource.calendar']
        for record in records.sorted(start_field):
            # include_public_holidays_in_duration=True: PH hours are part of leave duration → use raw schedule
            # default (False): PH not counted in duration → subtract them (compute_leaves=True equivalent)
            wet = record.work_entry_type_id
            include_ph = wet._fields.get('include_public_holidays_in_duration') and wet.include_public_holidays_in_duration
            emp_schedule = base_raw_sched[record.employee_id] if include_ph else base_sched_no_ph[record.employee_id]
            segs = record._get_pipeline_intervals_local(emp_schedule)
            for seg_start, seg_stop in segs:
                active_iv[record.employee_id][record] |= Intervals([(seg_start, seg_stop, dummy)])
                pipeline_by_emp[record.employee_id].append(
                    _Iv(seg_start, seg_stop, record.work_entry_type_id, record, None, frozenset())
                )

        for rule in applicable_rules:
            work_intervals = work_intervals_by_calendar[rule._get_schedule_calendar().id or False]
            rule_window_by_emp = rule._build_rule_day_intervals(start_dt, end_dt, employees, work_intervals)
            condition_wets = rule.condition_work_entry_type_ids
            # true when threshold evaluation requires schedule data (calendar_source set or
            # explicit expected_hours > 0); false means any matching interval is implicitly
            # "excess" and we can skip _evaluate_period entirely for pp/alloc-only rules.
            uses_schedule = bool(rule.calendar_source or rule.expected_hours)

            for employee in rule._get_applicable_employees(employees):
                emp_pipeline = pipeline_by_emp[employee]
                rule_window = rule_window_by_emp[employee]

                # filter by condition time type (single pass)
                matching, non_matching = [], []
                for iv in emp_pipeline:
                    (matching if iv.wet in condition_wets else non_matching).append(iv)
                if not matching:
                    _logger.warning(
                        "rule '%s' (id=%d) skipped for %s: no pipeline intervals match "
                        "condition WETs %s (pipeline WETs: %s)",
                        rule.name, rule.id, employee.name,
                        condition_wets.mapped('name'),
                        list({iv.wet.name for iv in emp_pipeline}),
                    )
                    continue

                # clip matching intervals to the rule's timing window
                inside, outside = _split_by_window(matching, rule_window)
                if not inside:
                    _logger.warning(
                        "rule '%s' (id=%d) skipped for %s: %d matching interval(s) "
                        "all fall outside the rule window",
                        rule.name, rule.id, employee.name, len(matching),
                    )
                    continue

                if not rule.work_entry_type_id and not uses_schedule:
                    # pp/alloc-only rule with no schedule threshold: tag all matching intervals
                    # directly as excess without loading schedule data.
                    # stack any displaced rule into acc so its pp and allocation are credited.
                    pipeline_by_emp[employee] = non_matching + outside + [
                        iv._replace(rule=rule, acc=iv.acc if iv.rule is None else iv.acc | {iv.rule})
                        for iv in inside
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
                for iv in inside:
                    day = iv.start.date()
                    if period == 'week':
                        week_start_int = int(rule.week_start or '0')
                        end_weekday = (week_start_int - 1) % 7
                        days_to_end = (end_weekday - day.weekday()) % 7
                        period_key = day + relativedelta(days=days_to_end)
                    else:
                        period_key = day
                    by_period[period_key].append((iv.start, iv.end, iv.source))

                all_excess = defaultdict(list)
                for period_date, period_items in sorted(by_period.items()):
                    period_stop = datetime.combine(period_date, datetime.max.time())
                    period_start = (
                        datetime.combine(period_date, datetime.min.time()) - relativedelta(days=6)
                        if period == 'week' else
                        datetime.combine(period_date, datetime.min.time())
                    )
                    period_window_iv = Intervals([(period_start, period_stop, self.env['resource.calendar'])])
                    if rule.calendar_source == 'employee' and not (period_window_iv - fully_flex):
                        continue
                    schedule_in_window = schedule & rule_window & period_window_iv
                    ex, df = rule._evaluate_period(period_start, period_stop, period_items, schedule_in_window)
                    for source, items in df.items():
                        deficit[employee][source].extend(items)
                        _logger.warning(
                            "rule '%s' (id=%d) → deficit for %s on source %s %d: %d interval(s)",
                            rule.name, rule.id, employee.name, source._name, source.id, len(items),
                        )
                    for source, items in ex.items():
                        all_excess[source].extend(items)
                        _logger.warning(
                            "rule '%s' (id=%d) → excess for %s on source %s %d: %d interval(s)",
                            rule.name, rule.id, employee.name, source._name, source.id, len(items),
                        )

                if not all_excess:
                    _logger.warning(
                        "rule '%s' (id=%d): no excess produced for %s (all periods below threshold)",
                        rule.name, rule.id, employee.name,
                    )
                    continue

                # split inside intervals at excess boundaries, reclassifying the excess portions
                new_inside = []
                for iv in inside:
                    if iv.source not in all_excess:
                        new_inside.append(iv)
                        continue
                    cursor = iv.start
                    for exc_start, exc_end, exc_rule in all_excess[iv.source]:
                        clip_start = max(cursor, exc_start)
                        clip_end = min(iv.end, exc_end)
                        if cursor < clip_start:
                            new_inside.append(iv._replace(start=cursor, end=clip_start))
                        if clip_start < clip_end:
                            # preserve source WET when the rule has no output type (allocate-only rules)
                            new_wet = exc_rule.work_entry_type_id or iv.wet
                            # stack the displaced rule into acc: it contributes pp and alloc credit
                            new_acc = iv.acc if iv.rule is None else iv.acc | {iv.rule}
                            new_inside.append(iv._replace(start=clip_start, end=clip_end, wet=new_wet, rule=exc_rule, acc=new_acc))
                        cursor = max(cursor, clip_end)
                    if cursor < iv.end:
                        new_inside.append(iv._replace(start=cursor))
                pipeline_by_emp[employee] = non_matching + outside + new_inside

        # extract final excess: pipeline intervals where a rule has classified them.
        for employee, emp_pipeline in pipeline_by_emp.items():
            for iv in emp_pipeline:
                if iv.rule is not None and iv.end > iv.start:
                    excess[employee][iv.source].append(iv)

        return excess, deficit, active_iv
