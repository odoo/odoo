# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from bisect import bisect_right
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from itertools import chain, islice, pairwise
from typing import NamedTuple
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import float_to_time, sum_intervals
from odoo.tools.float_utils import float_compare
from odoo.tools.intervals import Intervals

SCHEDULE_BASED_WORKING_HOURS_MODES = ('schedule_day', 'schedule_week')
DAILY_WORKING_HOURS_MODES = ('schedule_day', 'day')
WEEKLY_WORKING_HOURS_MODES = ('schedule_week', 'week')

# Below this amount of hours, a deficit is considered as entirely placed.
HOURS_EPSILON = 1e-6


class PipelineInterval(NamedTuple):
    """A slice of a time record (attendance or leave) travelling through the rule pipeline.

    Rules are applied one after the other (by sequence). Each rule may cut a slice into smaller
    ones and reclassify some of them. Datetimes are naive and expressed in the employee's timezone.
    """
    start: datetime
    end: datetime
    # current work entry type, replaced each time a rule reclassifies the slice
    work_entry_type: models.BaseModel
    # hr.attendance or hr.leave the slice was cut from
    source_record: models.BaseModel = None
    # last rule that reclassified the slice; None while the slice is untouched
    classifying_rule: models.BaseModel = None
    # rules that classified the slice before a later rule took over; they produce no record
    # but still earn their premium pay and allocation credit
    displaced_rules: frozenset = frozenset()
    # premium pay category ids, only filled when resolving the final outputs
    premium_pay_category_ids: frozenset = frozenset()

    def duration_hours(self):
        return _hours_between(self.start, self.end)

    def reclassified_by(self, rule, **changes):
        """Return a copy classified by `rule`; the previous classifying rule becomes a displaced one."""
        displaced_rules = self.displaced_rules
        if self.classifying_rule is not None:
            displaced_rules = displaced_rules | {self.classifying_rule}
        return self._replace(classifying_rule=rule, displaced_rules=displaced_rules, **changes)


class _OutputPlan:
    """What `hr.time.rule._apply_output` decides to create, gathered for a single batched create()."""

    def __init__(self):
        self.vals_list_to_create = []
        # each allocation credit is a list [employee, rule, hours, source record, record to log the credit on]
        self.excess_allocation_credits = []
        self.deficit_allocation_credits = []
        # (allocation credit, index in vals_list_to_create): credits to log on a record not created yet
        self._allocation_credits_waiting_for_their_record = []

    def add_record_to_create(self, vals):
        self.vals_list_to_create.append(vals)

    def add_output_record_to_create(self, vals, allocation_credits, employee, rule, hours, source_record):
        """Plan an output record whose allocation credit is logged on the output itself, so that
        deleting the output reverses exactly its own credit."""
        allocation_credit = [employee, rule, hours, source_record, None]
        allocation_credits.append(allocation_credit)
        self._allocation_credits_waiting_for_their_record.append((allocation_credit, len(self.vals_list_to_create)))
        self.vals_list_to_create.append(vals)

    def link_allocation_credits_to_created_records(self, created_records):
        for allocation_credit, vals_index in self._allocation_credits_waiting_for_their_record:
            allocation_credit[4] = created_records[vals_index]


def resolve_intervals_by_sequence(intervals):
    """For each non-overlapping sub-interval, pick the payload with the lowest sequence.

    intervals: iterable of (start, stop, payload) where payload has a .sequence attribute.
    Zero-duration slices are silently dropped.
    Returns a list of (start, stop, payload) with no overlaps.
    """
    non_empty_intervals = [(start, stop, payload) for start, stop, payload in intervals if stop > start]
    boundaries = sorted({moment for start, stop, _payload in non_empty_intervals for moment in (start, stop)})
    resolved_intervals = []
    for slice_start, slice_stop in pairwise(boundaries):
        covering_payloads = (
            payload for start, stop, payload in non_empty_intervals
            if start <= slice_start and slice_stop <= stop
        )
        winning_payload = min(covering_payloads, key=lambda payload: payload.sequence, default=None)
        if winning_payload:
            resolved_intervals.append((slice_start, slice_stop, winning_payload))
    return resolved_intervals


def _hours_between(start, stop):
    return (stop - start).total_seconds() / 3600


def _as_date(value):
    return value.date() if isinstance(value, datetime) else value


def _strip_timezone(intervals):
    """Return a new Intervals object whose datetimes have no tzinfo anymore."""
    return Intervals([
        (start.replace(tzinfo=None), stop.replace(tzinfo=None), payload)
        for start, stop, payload in intervals
    ])


def local_to_utc(local_naive_datetime, timezone):
    """Convert a naive datetime expressed in `timezone` to a naive UTC datetime."""
    return local_naive_datetime.replace(tzinfo=timezone).astimezone(UTC).replace(tzinfo=None)


def utc_to_local(utc_naive_datetime, timezone):
    """Convert a naive UTC datetime to a naive datetime expressed in `timezone`."""
    return utc_naive_datetime.replace(tzinfo=UTC).astimezone(timezone).replace(tzinfo=None)


def _drop_leading_hours(intervals, hours_to_drop):
    """Remove `hours_to_drop` hours from the beginning of a chronological list of intervals."""
    kept_intervals = []
    for start, stop, payload in intervals:
        if hours_to_drop <= 0:
            kept_intervals.append((start, stop, payload))
            continue
        interval_hours = _hours_between(start, stop)
        if interval_hours <= hours_to_drop:
            hours_to_drop -= interval_hours
            continue
        kept_intervals.append((start + timedelta(hours=hours_to_drop), stop, payload))
        hours_to_drop = 0
    return kept_intervals


def _split_by_window(pipeline_intervals, window):
    """Cut pipeline intervals along a rule window.

    :param window: Intervals object (sorted, non-overlapping segments)
    :return: (parts inside the window, parts outside the window)
    """
    inside_window = []
    outside_window = []
    window_segments = [(window_start, window_stop) for window_start, window_stop, _payload in window]
    window_stops = [window_stop for _window_start, window_stop in window_segments]
    for interval in pipeline_intervals:
        cursor = interval.start
        # skip the window segments ending before the interval starts
        first_segment_index = bisect_right(window_stops, interval.start)
        for window_start, window_stop in islice(window_segments, first_segment_index, None):
            if window_start >= interval.end:
                break
            overlap_start = max(interval.start, window_start)
            overlap_stop = min(interval.end, window_stop)
            if cursor < overlap_start:
                outside_window.append(interval._replace(start=cursor, end=overlap_start))
            inside_window.append(interval._replace(start=overlap_start, end=overlap_stop))
            cursor = overlap_stop
        if cursor < interval.end:
            outside_window.append(interval._replace(start=cursor, end=interval.end))
    return inside_window, outside_window


def _reclassify_excess_parts(pipeline_intervals, excess_by_source):
    """Cut pipeline intervals at the excess boundaries and reclassify the excess parts.

    :param excess_by_source: {source record: [(start, stop, rule having found the excess)]}
    """
    result = []
    for interval in pipeline_intervals:
        source_excess = excess_by_source.get(interval.source_record)
        if source_excess is None:
            result.append(interval)
            continue
        cursor = interval.start
        for excess_start, excess_stop, excess_rule in source_excess:
            if excess_start >= interval.end:
                break
            overlap_start = max(cursor, excess_start)
            overlap_stop = min(interval.end, excess_stop)
            if cursor < overlap_start:
                result.append(interval._replace(start=cursor, end=overlap_start))
            if overlap_start < overlap_stop:
                result.append(interval.reclassified_by(
                    excess_rule,
                    start=overlap_start,
                    end=overlap_stop,
                    # a rule without output type (allocation only) keeps the current type
                    work_entry_type=excess_rule.work_entry_type_id or interval.work_entry_type,
                ))
            cursor = max(cursor, overlap_stop)
        if cursor < interval.end:
            result.append(interval._replace(start=cursor))
    return result


def _prorated_break_hours(break_by_source, source_record, interval_seconds):
    """Part of the source's break falling in an interval, proportionally to the interval length.

    :param break_by_source: {source record: (span of the source in seconds, break hours)}
    """
    if source_record not in break_by_source:
        return 0.0
    span_seconds, break_hours = break_by_source[source_record]
    return interval_seconds / span_seconds * break_hours


def _write_without_retriggering_rules(record, vals):
    record.sudo().with_context(**record._time_rule_write_ctx).write(vals)


class HrTimeRule(models.Model):
    """Threshold rule reclassifying worked or absent time (overtime, undertime).

    A rule reads: when the time of the types ``condition_work_entry_type_ids`` within the
    timing window (weekdays, public holidays, ``timing_start``-``timing_stop``) exceeds
    (``threshold_operator = 'exceed'``) or is less than (``'less_than'``) the expected hours of
    the period (``quantity_period``: day or week, from the schedule or ``expected_hours``, see
    ``working_hours_mode``), the excess or the missing time gets the type
    ``work_entry_type_id``. ``employer_tolerance`` / ``employee_tolerance`` are the hours
    ignored before an excess / a deficit counts.

    Rules are evaluated by :meth:`_evaluate_rules` on ``hr.attendance`` and ``hr.leave``
    records (the sources, see ``hr.time.rule.source.mixin``) and their result is written back
    on the sources by :meth:`_apply_output`.
    """

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

    @api.constrains('employee_domain')
    def _check_employee_domain(self):
        for rule in self:
            rule._get_employee_domain()

    @api.depends('threshold_operator', 'working_hours_mode', 'expected_hours', 'timing_start', 'timing_stop')
    def _compute_condition_label(self):
        def format_hour(hours):
            hour, minute = divmod(round(hours * 60), 60)
            return f"{hour:02d}:{minute:02d}"

        for rule in self:
            operator_symbol = '>' if rule.threshold_operator == 'exceed' else '<'
            period_label = self.env._('day') if rule.working_hours_mode in DAILY_WORKING_HOURS_MODES else self.env._('week')
            if rule.working_hours_mode in SCHEDULE_BASED_WORKING_HOURS_MODES:
                label = self.env._('%(op)s schedule/%(period)s', op=operator_symbol, period=period_label)
            else:
                label = self.env._('%(op)s %(hours)gh/%(period)s', op=operator_symbol, hours=rule.expected_hours, period=period_label)
            if rule.timing_start != 0 or rule.timing_stop != 24:
                label += ' ' + self.env._('%(from)s-%(to)s', **{'from': format_hour(rule.timing_start), 'to': format_hour(rule.timing_stop)})
            rule.condition_label = label

    @api.depends('company_id')
    def _compute_country_id(self):
        for rule in self:
            if rule.company_id:
                rule.country_id = rule.company_id.country_id

    @api.depends('country_id', 'company_id')
    def _compute_country_work_entry_type_ids(self):
        """A rule may use the work entry types of its country, or the generic ones
        (without country) if its country has no localized types."""
        WorkEntryType = self.env['hr.work.entry.type']
        country_by_rule = {rule: rule.country_id or rule.company_id.country_id for rule in self}
        country_ids = list({country.id for country in country_by_rule.values() if country})
        work_entry_types_by_country_id = WorkEntryType.search(
            [('country_id', 'in', [*country_ids, False])],
        ).grouped(lambda work_entry_type: work_entry_type.country_id.id)
        generic_work_entry_types = work_entry_types_by_country_id.get(False, WorkEntryType)
        for rule in self:
            country = country_by_rule[rule]
            rule.country_work_entry_type_ids = work_entry_types_by_country_id.get(country.id, generic_work_entry_types)

    @api.depends('work_entry_type_id.amount_rate')
    def _compute_amount_rate(self):
        for rule in self:
            rule.amount_rate = rule.work_entry_type_id.amount_rate if rule.work_entry_type_id else 1.0

    @api.depends('working_hours_mode')
    def _compute_calendar_source(self):
        for rule in self:
            if rule.working_hours_mode not in SCHEDULE_BASED_WORKING_HOURS_MODES:
                rule.calendar_source = False
            elif not rule.calendar_source:
                rule.calendar_source = 'employee'

    @api.depends('working_hours_mode')
    def _compute_quantity_period(self):
        for rule in self:
            if rule.working_hours_mode in DAILY_WORKING_HOURS_MODES:
                rule.quantity_period = 'day'
            elif rule.working_hours_mode in WEEKLY_WORKING_HOURS_MODES:
                rule.quantity_period = 'week'
            else:
                rule.quantity_period = False

    @api.depends('working_hours_mode')
    def _compute_expected_hours(self):
        for rule in self:
            if rule.working_hours_mode in SCHEDULE_BASED_WORKING_HOURS_MODES:
                rule.expected_hours = 0.0

    # ------------------------------------------------------------
    # Rule configuration helpers
    # ------------------------------------------------------------

    def _get_invalid_employee_domain_error(self, error):
        return ValidationError(self.env._(
            "Rule '%(name)s': invalid employee domain %(domain)s — %(error)s",
            name=self.name,
            domain=self.employee_domain,
            error=error,
        ))

    def _get_employee_domain(self):
        """Return the parsed `employee_domain`, or raise a ValidationError if it is malformed."""
        self.ensure_one()
        if not self.employee_domain or self.employee_domain == '[]':
            return []
        try:
            return literal_eval(self.employee_domain)
        except Exception as error:  # noqa: BLE001
            raise self._get_invalid_employee_domain_error(error) from error

    def _get_applicable_employees(self, employees):
        """Return the employees of ``employees`` the rule applies to.

        Filters on the rule's company (or else country), then on ``employee_domain`` (evaluated as
        superuser). ``hr_attendance`` also drops employees without calendar for rules based on the
        employee schedule.

        :param employees: ``hr.employee`` recordset
        :rtype: hr.employee
        :raise ValidationError: if ``employee_domain`` cannot be evaluated
        """
        self.ensure_one()
        if self.company_id:
            employees = employees.filtered(lambda employee: employee.company_id == self.company_id)
        elif self.country_id:
            employees = employees.filtered(lambda employee: employee.company_id.country_id == self.country_id)
        employee_domain = self._get_employee_domain() if employees else []
        if not employee_domain:
            return employees
        try:
            return employees.sudo().filtered_domain(employee_domain)
        except Exception as error:  # noqa: BLE001
            raise self._get_invalid_employee_domain_error(error) from error

    def _get_applies_on_weekday_flags(self):
        """Return 7 booleans, indexed like `date.weekday()` (0 = Monday)."""
        self.ensure_one()
        return [
            self.apply_monday, self.apply_tuesday, self.apply_wednesday,
            self.apply_thursday, self.apply_friday, self.apply_saturday, self.apply_sunday,
        ]

    def _get_period_last_day(self, day):
        """Return the last day of the rule period (day or week) containing `day`."""
        self.ensure_one()
        if self.quantity_period != 'week':
            return day
        first_weekday = int(self.week_start or '0')
        last_weekday = (first_weekday - 1) % 7
        return day + timedelta(days=(last_weekday - day.weekday()) % 7)

    def _get_schedule_calendar(self):
        """Return the reference calendar of the rule.

        :return: ``resource_calendar_id``, else the company's calendar when ``calendar_source``
            is ``'reference'``; an empty recordset otherwise (the rule relies on the employees' own
            calendars, or on their company's calendar, see :meth:`_get_work_intervals_key`)
        :rtype: resource.calendar
        """
        self.ensure_one()
        if self.calendar_source != 'reference':
            return self.env['resource.calendar']
        return self.resource_calendar_id or self.company_id.resource_calendar_id

    def _get_work_intervals_key(self):
        """Return the key of the rule's baseline in :meth:`_build_work_intervals_by_baseline`:
        ``False`` for the employees' own schedules, the id of the reference calendar, or
        ``'company'`` for the calendar of each employee's company (reference rule without
        calendar nor company)."""
        self.ensure_one()
        if self.calendar_source != 'reference':
            return False
        return self._get_schedule_calendar().id or 'company'

    def _get_premium_pay_category_ids(self):
        """Return the premium pay ids attached to the intervals this rule classifies.

        Hook for localizations (``l10n_be``); default: empty.

        :rtype: frozenset
        """
        self.ensure_one()
        return frozenset()

    def _get_source_annotation_vals(self, premium_pay_category_ids=frozenset()):
        """Return extra values written on a source record reused as the first output.

        When the output starts with the source, the source itself is reclassified (written)
        instead of creating a new record. Override to write the fields the
        ``_get_output_*_vals`` methods set on new output records (e.g.
        ``l10n_be_premium_pay_rule_ids``).

        :param frozenset premium_pay_category_ids: premium pay ids of the output interval(s)
        :rtype: dict
        """
        return {}

    # ------------------------------------------------------------
    # Expected working time
    # ------------------------------------------------------------

    def _build_work_intervals_by_baseline(self, employees, start_dt, end_dt):
        """Compute :meth:`_get_work_intervals` once per baseline calendar used by the rules of ``self``.

        :return: ``{key: work_intervals}``, keyed by :meth:`_get_work_intervals_key`
        :rtype: dict
        """
        work_intervals_by_baseline = {}
        for rule in self:
            work_intervals_key = rule._get_work_intervals_key()
            if work_intervals_key in work_intervals_by_baseline:
                continue
            if work_intervals_key is False:
                work_intervals = self._get_work_intervals(employees, start_dt, end_dt)
            elif work_intervals_key == 'company':
                # the rule belongs to no company: each employee is compared with their own company's calendar
                work_intervals = defaultdict(lambda: defaultdict(Intervals))
                for company, company_employees in employees.grouped('company_id').items():
                    company_work_intervals = self._get_work_intervals(
                        company_employees, start_dt, end_dt, schedule_calendar=company.resource_calendar_id,
                    )
                    for interval_type, intervals_by_employee in company_work_intervals.items():
                        work_intervals[interval_type].update(intervals_by_employee)
            else:
                work_intervals = self._get_work_intervals(
                    employees, start_dt, end_dt, schedule_calendar=rule._get_schedule_calendar(),
                )
            work_intervals_by_baseline[work_intervals_key] = work_intervals
        return work_intervals_by_baseline

    def _get_calendar_attendances_and_public_holidays(self, calendar, timezone, start, stop):
        """Return (attendance intervals, public holiday intervals) of `calendar`, in local naive datetimes."""
        no_resource_per_tz = {timezone: self.env['resource.resource']}
        attendances_by_resource_id = calendar._attendance_intervals_batch(start, stop, resources_per_tz=no_resource_per_tz)
        public_holidays_by_resource_id = calendar._leave_intervals_batch(
            start, stop, resources_per_tz=no_resource_per_tz, domain=[('resource_id', '=', False)],
        )
        return (
            _strip_timezone(attendances_by_resource_id.get(False, [])),
            _strip_timezone(public_holidays_by_resource_id.get(False, [])),
        )

    def _get_work_intervals(self, employees, start_dt, end_dt, schedule_calendar=None):
        """Return the schedule data the rules compare worked time with, per employee.

        Computed per version period of each employee, with naive datetimes in the employee's
        timezone (as all the pipeline).

        :param employees: ``hr.employee`` recordset
        :param datetime start_dt: period start (only the date is used, as a day of the
            employee's timezone)
        :param datetime end_dt: period end (only the date is used)
        :param schedule_calendar: reference ``resource.calendar`` replacing the versions'
            calendars for the ``'schedule'`` and ``'public_leave'`` keys
        :return: ``{key: {employee: Intervals}}`` with keys
            - ``'schedule'``: planned attendances,
            - ``'public_leave'``: global leaves of the calendar,
            - ``'leave'``: absence leaves of the employee,
            - ``'fully_flexible'``: version periods with a fully flexible calendar.
        :rtype: dict
        """
        version_periods_by_employee = employees.sudo()._get_version_periods(start_dt.date(), end_dt.date())
        work_intervals = {
            'schedule': defaultdict(Intervals),
            'leave': defaultdict(Intervals),
            'public_leave': defaultdict(Intervals),
            'fully_flexible': defaultdict(Intervals),
        }
        # (calendar id, timezone, start, stop) -> (attendance intervals, public holiday intervals)
        calendar_intervals_cache = {}
        # (calendar, start, stop) -> [(employee, timezone, version period)], to fetch the leaves in batch
        employees_by_leave_query = defaultdict(list)

        for employee, version_periods in version_periods_by_employee.items():
            timezone = ZoneInfo(employee.tz or 'UTC')
            for period_first_day, period_last_day, version in version_periods:
                period_start = datetime.combine(period_first_day, time.min, tzinfo=timezone)
                # the end of the period excluded, at the start of the day after its last day
                period_stop = datetime.combine(period_last_day + timedelta(days=1), time.min, tzinfo=timezone)
                version_period = Intervals([(period_start.replace(tzinfo=None), period_stop.replace(tzinfo=None), version)])

                if version._is_fully_flexible():
                    work_intervals['fully_flexible'][employee] |= version_period
                    if not schedule_calendar:
                        # the employee's own calendar is the baseline and there is none: nothing to compare with
                        continue

                employee_calendar = version.resource_calendar_id
                baseline_calendar = schedule_calendar or employee_calendar
                cache_key = (baseline_calendar.id, timezone, period_start, period_stop)
                if cache_key not in calendar_intervals_cache:
                    calendar_intervals_cache[cache_key] = self._get_calendar_attendances_and_public_holidays(
                        baseline_calendar, timezone, period_start, period_stop,
                    )
                attendance_intervals, public_holiday_intervals = calendar_intervals_cache[cache_key]
                work_intervals['schedule'][employee] |= attendance_intervals & version_period
                work_intervals['public_leave'][employee] |= public_holiday_intervals & version_period

                if employee_calendar:
                    employees_by_leave_query[employee_calendar, period_start, period_stop].append(
                        (employee, timezone, version_period),
                    )

        for (employee_calendar, period_start, period_stop), employee_periods in employees_by_leave_query.items():
            resources_per_tz = defaultdict(lambda: self.env['resource.resource'])
            for employee, timezone, _version_period in employee_periods:
                resources_per_tz[timezone] |= employee.resource_id
            leaves_by_resource_id = employee_calendar._leave_intervals_batch(
                period_start, period_stop, resources_per_tz=dict(resources_per_tz),
                domain=[('resource_id', '!=', False), ('count_as', '=', 'absence')],
            )
            for employee, _timezone, version_period in employee_periods:
                employee_leaves = _strip_timezone(leaves_by_resource_id.get(employee.resource_id.id, []))
                work_intervals['leave'][employee] |= employee_leaves & version_period

        return work_intervals

    # ------------------------------------------------------------
    # Rule window: the days and hours a rule applies on
    # ------------------------------------------------------------

    def _get_days_touched_by(self, intervals):
        """Return the set of dates overlapped by `intervals`.

        An interval starting at the very last instant of a day, or stopping at midnight,
        does not count for that day.
        """
        days = set()
        for start, stop, *_payload in intervals:
            if start.time() == time.max:
                start += timedelta(days=1)
            if stop.time() == time.min:
                stop -= timedelta(days=1)
            day, last_day = start.date(), stop.date()
            while day <= last_day:
                days.add(day)
                day += timedelta(days=1)
        return days

    def _get_timing_window(self, days):
        """Return the [timing_start, timing_stop] hours of the rule, on each of `days`."""
        self.ensure_one()
        window_start_time = float_to_time(self.timing_start)
        window_stop_time = float_to_time(self.timing_stop)
        no_payload = self.env['resource.calendar']
        return Intervals([
            (datetime.combine(day, window_start_time), datetime.combine(day, window_stop_time), no_payload)
            for day in days
        ])

    def _build_rule_day_intervals(self, range_start, range_stop, employees, work_intervals):
        """Return the timing window of the rule, per employee.

        The days of ``[range_start, range_stop]`` enabled by the ``apply_<weekday>`` flags, plus
        or minus the employee's public holidays (``apply_on_public_holidays``), restricted to the
        rule's hours (:meth:`_get_timing_window`).

        :param work_intervals: result of :meth:`_get_work_intervals`
        :return: ``{employee: Intervals}`` of naive local datetimes
        :rtype: dict
        """
        self.ensure_one()
        applies_on_weekday = self._get_applies_on_weekday_flags()
        selected_days = set()
        day, last_day = _as_date(range_start), _as_date(range_stop)
        while day <= last_day:
            if applies_on_weekday[day.weekday()]:
                selected_days.add(day)
            day += timedelta(days=1)

        # employees usually share the same public holidays, hence the same window
        window_by_public_holidays = {}
        rule_window_by_employee = {}
        for employee in employees:
            public_holidays = frozenset(self._get_days_touched_by(work_intervals['public_leave'][employee]))
            if public_holidays not in window_by_public_holidays:
                if self.apply_on_public_holidays:
                    applicable_days = selected_days | public_holidays
                else:
                    applicable_days = selected_days - public_holidays
                window_by_public_holidays[public_holidays] = self._get_timing_window(applicable_days)
            rule_window_by_employee[employee] = window_by_public_holidays[public_holidays]
        return rule_window_by_employee

    # ------------------------------------------------------------
    # Pipeline evaluation
    # ------------------------------------------------------------

    def _evaluate_rules(self, records, start_dt, end_dt):
        """Run the rules of ``self`` in sequence on source records; nothing is written.

        The sources are turned into a pipeline of ``PipelineInterval`` (naive local datetimes,
        see ``_get_pipeline_intervals_local``). Each applicable rule, in ``sequence, id`` order,
        takes the intervals whose current type is in its ``condition_work_entry_type_ids`` and
        inside its timing window, evaluates each period (:meth:`_evaluate_period`) and
        reclassifies the excess in the pipeline, so later rules see the output of earlier ones
        (e.g. a ``> 9h`` rule then a ``> 8h`` rule on the remaining attendance type). Rules
        without output type and without threshold just tag the matching intervals. Pass the
        result to :meth:`_apply_output`.

        :param records: source records (``hr.attendance`` or ``hr.leave``)
        :param datetime start_dt: evaluated period start (only the date is used, as a day of the
            employees' timezone)
        :param datetime end_dt: evaluated period end (only the date is used)
        :return: ``(excess, deficit, source_intervals_by_employee)``, each keyed by employee then source record:
            - ``excess``: ``[PipelineInterval]`` classified by a rule (premium pay ids not
              resolved yet, see :meth:`_resolve_output_intervals`),
            - ``deficit``: ``[(start, stop, rule)]`` missing hours,
            - ``source_intervals_by_employee``: ``Intervals``, the pipeline segments of the source.
        :rtype: tuple
        """
        excess = defaultdict(lambda: defaultdict(list))
        deficit = defaultdict(lambda: defaultdict(list))
        source_intervals_by_employee = defaultdict(lambda: defaultdict(Intervals))
        if not records:
            return excess, deficit, source_intervals_by_employee

        employees = records.employee_id
        applicable_employees_by_rule = {rule: rule._get_applicable_employees(employees) for rule in self}
        applicable_rules = self.filtered(lambda rule: applicable_employees_by_rule[rule])
        if not applicable_rules:
            return excess, deficit, source_intervals_by_employee

        work_intervals_by_baseline = applicable_rules._build_work_intervals_by_baseline(employees, start_dt, end_dt)
        pipeline_by_employee = self._build_initial_pipeline(records, employees, work_intervals_by_baseline, source_intervals_by_employee)

        for rule in applicable_rules:
            rule._apply_rule_on_pipeline(
                pipeline_by_employee, applicable_employees_by_rule[rule],
                work_intervals_by_baseline, start_dt, end_dt, deficit,
            )

        # at the end of the pipeline, every interval classified by a rule is an excess
        for employee, pipeline in pipeline_by_employee.items():
            for interval in pipeline:
                if interval.classifying_rule is not None and interval.end > interval.start:
                    excess[employee][interval.source_record].append(interval)

        return excess, deficit, source_intervals_by_employee

    def _build_initial_pipeline(self, records, employees, work_intervals_by_baseline, source_intervals_by_employee):
        """Cut every time record into its initial, unclassified pipeline intervals.

        Most records give a single interval; absences are clipped to the schedule. Like
        `_get_durations`, public holidays are removed from that schedule unless the leave
        type counts them in its duration.

        :param source_intervals_by_employee: filled with the intervals of each record, per employee
        :return: {employee: [PipelineInterval]}
        """
        base_work_intervals = (
            work_intervals_by_baseline.get(False)
            or next(iter(work_intervals_by_baseline.values()), {})
        )
        schedule_by_employee = base_work_intervals.get('schedule', defaultdict(Intervals))
        public_holidays_by_employee = base_work_intervals.get('public_leave', defaultdict(Intervals))
        schedule_without_public_holidays_by_employee = {
            employee: schedule_by_employee[employee] - public_holidays_by_employee[employee]
            for employee in employees
        }

        no_payload = self.env['resource.calendar']
        pipeline_by_employee = defaultdict(list)
        for record in records.sorted(records._time_rule_span_start_field):
            employee = record.employee_id
            work_entry_type = record.work_entry_type_id
            counts_public_holidays = (
                work_entry_type._fields.get('include_public_holidays_in_duration')
                and work_entry_type.include_public_holidays_in_duration
            )
            if counts_public_holidays:
                schedule = schedule_by_employee[employee]
            else:
                schedule = schedule_without_public_holidays_by_employee[employee]
            record_intervals = record._get_pipeline_intervals_local(schedule)
            if not record_intervals:
                continue
            source_intervals_by_employee[employee][record] |= Intervals([(start, stop, no_payload) for start, stop in record_intervals])
            pipeline_by_employee[employee].extend(
                PipelineInterval(start, stop, work_entry_type, record) for start, stop in record_intervals
            )
        return pipeline_by_employee

    def _apply_rule_on_pipeline(self, pipeline_by_employee, employees, work_intervals_by_baseline, start_dt, end_dt, deficit):
        """Apply this rule on the pipeline of each of `employees`.

        The excess parts are reclassified in `pipeline_by_employee`; the deficits are added to `deficit`.
        """
        self.ensure_one()
        work_intervals = work_intervals_by_baseline[self._get_work_intervals_key()]
        rule_window_by_employee = self._build_rule_day_intervals(start_dt, end_dt, employees, work_intervals)
        condition_work_entry_type_ids = set(self.condition_work_entry_type_ids.ids)
        # Without output type nor hours threshold (premium pay or allocation only rule), every
        # matching interval is excess: no need to compare periods with a schedule.
        everything_matching_is_excess = not self.work_entry_type_id and not (self.calendar_source or self.expected_hours)

        for employee in employees:
            matching_intervals, other_intervals = [], []
            for interval in pipeline_by_employee[employee]:
                if interval.work_entry_type.id in condition_work_entry_type_ids:
                    matching_intervals.append(interval)
                else:
                    other_intervals.append(interval)
            if not matching_intervals:
                continue

            rule_window = rule_window_by_employee[employee]
            inside_window, outside_window = _split_by_window(matching_intervals, rule_window)
            if not inside_window:
                continue

            if everything_matching_is_excess:
                pipeline_by_employee[employee] = (
                    other_intervals + outside_window + [interval.reclassified_by(self) for interval in inside_window]
                )
                continue

            excess_by_source = self._evaluate_employee_periods(employee, inside_window, work_intervals, rule_window, deficit)
            if excess_by_source:
                pipeline_by_employee[employee] = (
                    other_intervals + outside_window + _reclassify_excess_parts(inside_window, excess_by_source)
                )

    def _evaluate_employee_periods(self, employee, pipeline_intervals, work_intervals, rule_window, deficit):
        """Evaluate each period (day or week) covered by `pipeline_intervals`.

        The deficits are added to `deficit`.

        :return: {source record: [(start, stop, rule)]} the excess found
        """
        self.ensure_one()
        no_payload = self.env['resource.calendar']
        schedule = (
            work_intervals['schedule'][employee]
            - work_intervals['leave'][employee]
            - work_intervals['public_leave'][employee]
        )
        schedule_in_rule_window = schedule & rule_window
        fully_flexible_periods = work_intervals['fully_flexible'][employee]

        intervals_by_period_last_day = defaultdict(list)
        for interval in pipeline_intervals:
            period_last_day = self._get_period_last_day(interval.start.date())
            intervals_by_period_last_day[period_last_day].append((interval.start, interval.end, interval.source_record))

        excess_by_source = defaultdict(list)
        for period_last_day, period_intervals in sorted(intervals_by_period_last_day.items()):
            period_first_day = period_last_day - timedelta(days=6) if self.quantity_period == 'week' else period_last_day
            period_start = datetime.combine(period_first_day, time.min)
            period_stop = datetime.combine(period_last_day, time.max)
            period_window = Intervals([(period_start, period_stop, no_payload)])
            if self.calendar_source == 'employee' and not (period_window - fully_flexible_periods):
                # fully flexible during the whole period: no schedule to compare with
                continue
            period_excess, period_deficit = self._evaluate_period(
                period_start, period_stop, period_intervals, schedule_in_rule_window & period_window,
            )
            for source_record, deficit_intervals in period_deficit.items():
                deficit[employee][source_record].extend(deficit_intervals)
            for source_record, excess_intervals in period_excess.items():
                excess_by_source[source_record].extend(excess_intervals)
        return excess_by_source

    def _evaluate_period(self, start, stop, record_intervals, schedule):
        """Compare the time worked in one period (day or week) with the rule's threshold.

        Expected hours: the schedule in the period if ``calendar_source`` is set, else
        ``expected_hours``. Worked hours: union of the source intervals minus their breaks
        (prorated to the part of the source in the period).

        - ``exceed``: when the excess is above ``employer_tolerance``, the expected hours are
          consumed in chronological order and what remains is the excess, taken from the end of
          the source intervals (:meth:`_get_period_excess`).
        - ``less_than``: when the deficit is above ``employee_tolerance``, the gaps of the schedule
          (or of the period) not covered by worked time form the deficit, all attached to the
          source ending last (:meth:`_get_period_deficit`).

        :param datetime start: period start, naive local
        :param datetime stop: period end, naive local
        :param list record_intervals: ``(start, stop, source)`` tuples of the period
        :param Intervals schedule: schedule restricted to the rule window and the period
        :return: ``(excess_by_source, deficit_by_source)``, each ``{source: [(start, stop,
            rule)]}``; at most one of them is non-empty
        :rtype: tuple
        """
        self.ensure_one()
        no_payload = self.env['resource.calendar']
        period_window = Intervals([(start, stop, no_payload)])

        raw_intervals_by_source = defaultdict(list)
        for interval_start, interval_stop, source_record in record_intervals:
            raw_intervals_by_source[source_record].append((interval_start, interval_stop, no_payload))
        worked_intervals_by_source = {
            source_record: Intervals(source_intervals) & period_window
            for source_record, source_intervals in raw_intervals_by_source.items()
        }
        worked_intervals = Intervals(chain.from_iterable(worked_intervals_by_source.values()))

        if self.calendar_source:
            expected_hours = sum_intervals(schedule & period_window)
        else:
            expected_hours = self.expected_hours

        # A source's break is spread over its whole span: e.g. a 2h break in an 8h attendance
        # counts for 1h in a 4h window. The break stays on the source record: outputs carry none.
        break_by_source = {}
        for source_record in worked_intervals_by_source:
            break_hours = source_record._get_time_rule_break_hours()
            if not break_hours:
                continue
            span_start = source_record[source_record._time_rule_span_start_field]
            span_stop = source_record[source_record._time_rule_span_end_field]
            span_seconds = (span_stop - span_start).total_seconds() if span_start and span_stop else 0
            if span_seconds > 0:
                break_by_source[source_record] = (span_seconds, break_hours)
        total_break_hours = 0.0
        for source_record, source_intervals in worked_intervals_by_source.items():
            for interval_start, interval_stop, _payload in source_intervals:
                interval_seconds = (interval_stop - interval_start).total_seconds()
                total_break_hours += _prorated_break_hours(break_by_source, source_record, interval_seconds)

        effective_worked_hours = sum_intervals(worked_intervals) - total_break_hours
        excess_hours = effective_worked_hours - expected_hours

        if self.threshold_operator == 'less_than':
            missing_hours = -excess_hours
            if float_compare(missing_hours, self.employee_tolerance, 5) != 1:
                return {}, {}
            deficit_by_source = self._get_period_deficit(
                stop, period_window, schedule, worked_intervals, worked_intervals_by_source,
                missing_hours, total_break_hours,
            )
            return {}, deficit_by_source

        if float_compare(excess_hours, self.employer_tolerance, 5) != 1:
            return {}, {}
        excess_by_source = self._get_period_excess(worked_intervals_by_source, break_by_source, expected_hours, excess_hours)
        return excess_by_source, {}

    def _get_period_deficit(self, stop, period_window, schedule, worked_intervals, worked_intervals_by_source, missing_hours, total_break_hours):
        """Place the missing hours of a period in the gaps of the schedule.

        :return: {last source of the period: [(start, stop, rule)]}
        """
        last_source = max(
            worked_intervals_by_source,
            key=lambda source_record: max(interval_stop for _start, interval_stop, _payload in worked_intervals_by_source[source_record]),
        )
        if self.calendar_source:
            gaps = list((schedule & period_window) - worked_intervals)
            hours_worked_outside_schedule = sum_intervals(worked_intervals) - sum_intervals(worked_intervals & schedule & period_window)
            if hours_worked_outside_schedule > 0:
                # hours worked outside the schedule fill the earliest gaps
                gaps = _drop_leading_hours(gaps, hours_worked_outside_schedule)
            if total_break_hours > 0:
                # the part of the deficit due to breaks is placed at the very end of the period
                gap_hours = sum(_hours_between(gap_start, gap_stop) for gap_start, gap_stop, _payload in gaps)
                break_deficit_hours = missing_hours - gap_hours
                if break_deficit_hours > HOURS_EPSILON:
                    gaps.append((stop - timedelta(hours=break_deficit_hours), stop, self.env['resource.calendar']))
        else:
            # Place the deficit in working time so the output lands within calendar hours, like
            # above. Fully flexible employees have no schedule: use the whole period instead.
            available_intervals = schedule if schedule else period_window
            free_intervals = available_intervals - worked_intervals
            gaps = list(free_intervals)
            superfluous_free_hours = sum_intervals(free_intervals) - missing_hours
            if superfluous_free_hours > 0:
                gaps = _drop_leading_hours(gaps, superfluous_free_hours)
        return {last_source: [(gap_start, gap_stop, self) for gap_start, gap_stop, _payload in gaps]}

    def _get_period_excess(self, worked_intervals_by_source, break_by_source, expected_hours, excess_hours):
        """Find the excess of a period: the expected hours are consumed chronologically,
        everything worked afterwards is excess.

        :return: {source record: [(start, stop, rule)]}
        """
        excess_by_source = defaultdict(list)
        remaining_expected_hours = expected_hours
        remaining_excess_hours = excess_hours
        sources_by_first_start = sorted(
            worked_intervals_by_source,
            key=lambda source_record: min(interval_start for interval_start, _stop, _payload in worked_intervals_by_source[source_record]),
        )
        for source_record in sources_by_first_start:
            for interval_start, interval_stop, _payload in worked_intervals_by_source[source_record]:
                interval_seconds = (interval_stop - interval_start).total_seconds()
                # the prorated break stays on the source record, it is never excess
                effective_hours = interval_seconds / 3600 - _prorated_break_hours(break_by_source, source_record, interval_seconds)
                if remaining_expected_hours >= effective_hours:
                    remaining_expected_hours -= effective_hours
                    continue
                interval_excess_hours = effective_hours - remaining_expected_hours
                remaining_expected_hours = 0
                excess_by_source[source_record].append((interval_stop - timedelta(hours=interval_excess_hours), interval_stop, self))
                remaining_excess_hours -= interval_excess_hours
                if remaining_excess_hours <= 0:
                    return excess_by_source
        return excess_by_source

    # ------------------------------------------------------------
    # Output: turn the pipeline result into records
    # ------------------------------------------------------------

    def _resolve_output_intervals(self, intervals):
        """Return the excess intervals of a source in their final output form.

        Sorts by start, drops empty intervals and intervals without type, sets ``work_entry_type``
        to the rule's ``work_entry_type_id`` (else the current type) and
        ``premium_pay_category_ids`` to the premium pay ids of the classifying rule and of the
        rules it displaced (``displaced_rules``). ``hr_holidays`` also merges consecutive slices
        with the same output.

        :param list intervals: ``PipelineInterval`` excess intervals of one source
        :rtype: list
        """
        resolved_intervals = []
        for interval in sorted(intervals, key=lambda interval: interval.start):
            output_work_entry_type = interval.classifying_rule.work_entry_type_id or interval.work_entry_type
            if not output_work_entry_type or interval.end <= interval.start:
                continue
            classifying_rules = interval.displaced_rules | {interval.classifying_rule}
            premium_pay_category_ids = frozenset().union(*(rule._get_premium_pay_category_ids() for rule in classifying_rules))
            resolved_intervals.append(interval._replace(
                work_entry_type=output_work_entry_type,
                premium_pay_category_ids=premium_pay_category_ids,
            ))
        return resolved_intervals

    @api.model
    def _group_deficit_intervals_by_period(self, deficit_intervals):
        """Group deficit intervals by period, keeping only those of the lowest-sequence rule of each period.

        Intervals without output type or without duration are dropped.

        :param deficit_intervals: [(start, stop, rule)]
        :return: {last day of the period: [(start, stop, rule)]}
        """
        intervals_by_period_last_day = defaultdict(list)
        for start, stop, rule in deficit_intervals:
            if rule.work_entry_type_id and start < stop:
                intervals_by_period_last_day[rule._get_period_last_day(start.date())].append((start, stop, rule))
        winning_intervals_by_period_last_day = {}
        for period_last_day, period_intervals in intervals_by_period_last_day.items():
            winning_rule = min(period_intervals, key=lambda interval: interval[2].sequence)[2]
            winning_intervals_by_period_last_day[period_last_day] = [
                interval for interval in period_intervals if interval[2] == winning_rule
            ]
        return winning_intervals_by_period_last_day

    def _apply_output(self, excess, deficit, source_intervals_by_employee=None):
        """Write the result of :meth:`_evaluate_rules` on the source records.

        Shared by attendances and leaves (called by ``_apply_attendance_output`` /
        ``_apply_leave_output``). Writes use the source's ``_time_rule_write_ctx``, so they do not
        trigger the rules again. New records are created in one batch.

        - Excess (:meth:`_plan_excess_outputs`): if the first output interval starts with the
          source, the source itself is reclassified (type, ``time_rule_id``, end); otherwise the
          source is cut at the first output start. Each other output interval becomes a new
          record (``_get_time_rule_output_vals``) and the uncovered parts of the source a
          remainder record keeping the source type (``_get_time_rule_remainder_vals``). Rules
          without output type only annotate the source (:meth:`_get_source_annotation_vals`).
        - Deficit (:meth:`_plan_deficit_outputs`): per period, only the lowest sequence rule is
          kept; the missing hours are placed as new output records in the free slots after the
          deficit start (not covered by other records of the model), minus what earlier runs
          already created.

        :param dict excess: ``{employee: {source: [PipelineInterval]}}``
        :param dict deficit: ``{employee: {source: [(start, stop, rule)]}}``
        :param dict source_intervals_by_employee: ``{employee: {source: Intervals}}`` pipeline segments of the
            sources, used to compute the remainders
        :return: ``(new_records, all_source_ids, excess_allocation_credits, deficit_allocation_credits)``: created records,
            ids of the processed sources, and allocation rows
            ``[employee, rule, hours, source, log_source]`` (``log_source`` = record the credit is
            logged on, used by ``hr_holidays`` for compensatory allocations). Returns
            ``(None, frozenset(), [], [])`` when there is no source.
        :rtype: tuple
        """
        plan = _OutputPlan()
        processed_source_ids = set()

        for employee, deficit_by_source in deficit.items():
            timezone = ZoneInfo(employee._get_tz())
            for source_record, deficit_intervals in deficit_by_source.items():
                processed_source_ids.add(source_record.id)
                self._plan_deficit_outputs(plan, employee, timezone, source_record, deficit_intervals)

        for employee, excess_by_source in excess.items():
            timezone = ZoneInfo(employee._get_tz())
            for source_record, excess_intervals in excess_by_source.items():
                processed_source_ids.add(source_record.id)
                self._plan_excess_outputs(plan, employee, timezone, source_record, excess_intervals, source_intervals_by_employee)

        any_source_record = next(chain(
            (source_record for excess_by_source in excess.values() for source_record in excess_by_source),
            (source_record for deficit_by_source in deficit.values() for source_record in deficit_by_source),
        ), None)
        if any_source_record is None:
            return None, frozenset(), [], []
        created_records = self.env[any_source_record._name].sudo().with_context(
            **any_source_record._time_rule_write_ctx,
        ).create(plan.vals_list_to_create)
        plan.link_allocation_credits_to_created_records(created_records)
        return created_records, processed_source_ids, plan.excess_allocation_credits, plan.deficit_allocation_credits

    def _plan_deficit_outputs(self, plan, employee, timezone, source_record, deficit_intervals):
        """Place the missing hours in the free time following each deficit, until the end of its period.

        Hours already covered by a previous run are not placed twice.
        """
        no_payload = self.env['resource.calendar']
        for period_last_day, winning_intervals in self._group_deficit_intervals_by_period(deficit_intervals).items():
            period_end_utc = local_to_utc(datetime.combine(period_last_day + timedelta(days=1), time.min), timezone)
            for deficit_start, deficit_stop, rule in winning_intervals:
                premium_pay_category_ids = rule._get_premium_pay_category_ids()
                deficit_start_utc = local_to_utc(deficit_start, timezone)
                occupied_intervals = source_record._get_time_rule_deficit_occupied(employee.id, deficit_start_utc, period_end_utc)
                already_covered_hours = source_record._get_time_rule_deficit_already_covered(rule, deficit_start_utc, period_end_utc)
                hours_to_place = max(0.0, _hours_between(deficit_start, deficit_stop) - already_covered_hours)
                free_slots = Intervals([(deficit_start_utc, period_end_utc, no_payload)]) - occupied_intervals
                for slot_start, slot_stop, _payload in free_slots:
                    if hours_to_place <= HOURS_EPSILON:
                        break
                    slot_hours = _hours_between(slot_start, slot_stop)
                    if slot_hours > hours_to_place:
                        slot_stop = slot_start + timedelta(hours=hours_to_place)
                        slot_hours = hours_to_place
                    plan.add_output_record_to_create(
                        source_record._get_time_rule_output_vals(rule, slot_start, slot_stop, premium_pay_category_ids),
                        plan.deficit_allocation_credits, employee, rule, slot_hours, source_record,
                    )
                    hours_to_place -= slot_hours

    def _plan_excess_outputs(self, plan, employee, timezone, source_record, excess_intervals, source_intervals_by_employee):
        # Displaced rules produce no record but still earn allocation for the hours they claimed.
        for interval in excess_intervals:
            if interval.end <= interval.start:
                continue
            interval_hours = interval.duration_hours()
            for displaced_rule in interval.displaced_rules:
                plan.excess_allocation_credits.append([employee, displaced_rule, interval_hours, source_record, source_record])

        output_intervals = self._resolve_output_intervals(excess_intervals)
        if not output_intervals:
            return
        if all(not interval.classifying_rule.work_entry_type_id for interval in output_intervals):
            self._annotate_source_without_split(plan, employee, source_record, output_intervals)
        else:
            self._split_source_into_outputs(plan, employee, timezone, source_record, output_intervals, source_intervals_by_employee)

    def _annotate_source_without_split(self, plan, employee, source_record, output_intervals):
        """Handle rules without output type (premium pay only): every interval keeps the source type,
        so the source is only annotated, never split. The excess hours are still credited, for
        callers allocating them."""
        all_premium_pay_category_ids = frozenset().union(*(interval.premium_pay_category_ids for interval in output_intervals))
        # every distinct classifying rule is asked, as overrides may depend on the rule
        annotation_vals = {}
        for classifying_rule in dict.fromkeys(interval.classifying_rule for interval in output_intervals):
            annotation_vals |= classifying_rule._get_source_annotation_vals(premium_pay_category_ids=all_premium_pay_category_ids)
        if annotation_vals:
            _write_without_retriggering_rules(source_record, annotation_vals)
        for interval in output_intervals:
            plan.excess_allocation_credits.append([employee, interval.classifying_rule, interval.duration_hours(), source_record, source_record])

    def _split_source_into_outputs(self, plan, employee, timezone, source_record, output_intervals, source_intervals_by_employee):
        """Cut the source record around its output intervals.

        If the first output starts at the very beginning of the source, the source itself becomes
        that output (in place). Otherwise, the source is shortened to end where the first output
        starts. All the other parts become new records: the remainders keep the source type, the
        outputs get their rule's type.
        """
        no_payload = self.env['resource.calendar']
        start_field = source_record._time_rule_span_start_field
        end_field = source_record._time_rule_span_end_field
        source_work_entry_type_id = source_record.work_entry_type_id.id

        source_intervals = (source_intervals_by_employee or {}).get(employee, {}).get(source_record)
        if source_intervals is None:
            source_intervals = Intervals([(
                utc_to_local(source_record[start_field], timezone),
                utc_to_local(source_record[end_field], timezone),
                no_payload,
            )])
        output_union = Intervals([(interval.start, interval.end, no_payload) for interval in output_intervals], keep_distinct=True)
        remainder_intervals = list(source_intervals - output_union)

        def plan_remainders(remainders):
            for remainder_start, remainder_stop, _payload in remainders:
                remainder_vals = source_record._get_time_rule_remainder_vals(
                    local_to_utc(remainder_start, timezone), local_to_utc(remainder_stop, timezone),
                )
                plan.add_record_to_create(remainder_vals | {'work_entry_type_id': source_work_entry_type_id})

        first_output_start_utc = min(local_to_utc(interval.start, timezone) for interval in output_intervals)
        if first_output_start_utc <= source_record[start_field]:
            first_output_interval = output_intervals[0]
            self._turn_source_into_output(source_record, first_output_interval, timezone)
            plan_remainders(remainder_intervals)
            # the source record is the output: the credit is logged on it
            plan.excess_allocation_credits.append([
                employee, first_output_interval.classifying_rule, first_output_interval.duration_hours(), source_record, source_record,
            ])
            output_intervals_to_create = output_intervals[1:]
        else:
            first_output_start_local = min(interval.start for interval in output_intervals)
            _write_without_retriggering_rules(
                source_record, source_record._get_time_rule_end_write_vals(first_output_start_utc, first_output_start_local),
            )
            # the first remainder is the shortened source record itself
            plan_remainders(remainder_intervals[1:])
            output_intervals_to_create = output_intervals

        for output_interval in output_intervals_to_create:
            output_vals = source_record._get_time_rule_output_vals(
                output_interval.classifying_rule,
                local_to_utc(output_interval.start, timezone),
                local_to_utc(output_interval.end, timezone),
                output_interval.premium_pay_category_ids,
            )
            plan.add_output_record_to_create(
                output_vals, plan.excess_allocation_credits, employee, output_interval.classifying_rule, output_interval.duration_hours(), source_record,
            )

    def _turn_source_into_output(self, source_record, output_interval, timezone):
        """Reclassify the source record in place so that it becomes `output_interval`."""
        output_end_utc = local_to_utc(output_interval.end, timezone)
        annotation_vals = output_interval.classifying_rule._get_source_annotation_vals(premium_pay_category_ids=output_interval.premium_pay_category_ids)
        is_already_the_output = (
            source_record.work_entry_type_id == output_interval.work_entry_type
            and source_record.time_rule_id == output_interval.classifying_rule
            and source_record[source_record._time_rule_span_end_field] == output_end_utc
        )
        if not is_already_the_output:
            _write_without_retriggering_rules(source_record, {
                'work_entry_type_id': output_interval.work_entry_type.id,
                'time_rule_id': output_interval.classifying_rule.id,
                **source_record._get_time_rule_end_write_vals(output_end_utc, output_interval.end),
                **annotation_vals,
            })
        elif annotation_vals:
            # the main fields already match, but the premium pay categories may still need an update
            _write_without_retriggering_rules(source_record, annotation_vals)
