# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime, time, timedelta, UTC
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.date_utils import sum_intervals
from odoo.tools.intervals import Intervals


def _to_local_date(employee, value):
    """Return the date of ``value`` in the timezone of ``employee``.

    :param employee: ``hr.employee``
    :param value: a date (returned as is) or a datetime, naive UTC or aware
    :rtype: date
    """
    if not isinstance(value, datetime):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ZoneInfo(employee.sudo()._get_tz())).date()


class HrTimeRuleSourceMixin(models.AbstractModel):
    """Make a model a source of the time rule pipeline (``hr.time.rule``).

    Inherited by ``hr.attendance`` and ``hr.leave``. Creating a source, or writing its employee,
    span or the fields of :meth:`_get_write_source_extra_source_fields`, triggers the rules
    (:meth:`_trigger_time_rules`) unless the context has ``skip_time_rules``. The rules then
    reclassify the source in place and/or create output records of the same model, linked to
    the source.

    The inheriting model must have ``employee_id``, ``work_entry_type_id`` and ``time_rule_id``
    fields, set the class attributes below and implement the hooks raising
    ``NotImplementedError``:

    - ``_time_rule_source_field``: many2one from an output record to its source
      (``source_attendance_id``, ``source_leave_id``);
    - ``_time_rule_output_field``: the inverse one2many (``overtime_attendance_ids``,
      ``output_leave_ids``);
    - ``_time_rule_span_start_field`` / ``_time_rule_span_end_field``: datetime fields (UTC)
      holding the span (``check_in``/``check_out``, ``date_from``/``date_to``);
    - ``_time_rule_write_ctx``: context used for the pipeline's own writes.
    """

    _name = 'hr.time.rule.source.mixin'
    _description = 'Time Rule Source Mixin'

    # subclasses declare these
    _time_rule_source_field = ''           # m2o from output to source
    _time_rule_output_field = ''           # o2m from source to output
    _time_rule_span_start_field = ''       # span start field name
    _time_rule_span_end_field = ''         # span end field name
    _time_rule_write_ctx = {'skip_time_rules': True, 'tracking_disable': True}

    active = fields.Boolean(default=True)
    time_rule_id = fields.Many2one('hr.time.rule', index=True)

    @api.model
    def _time_rule_wizard_extra_domain(self):
        """Extra domain applied when searching this model in the reprocess wizard."""
        return []

    def _apply_record_output(self, rules, excess, deficit, active_iv=None):
        """Write the pipeline result on the records; must be implemented.

        Implementations delegate to a ``hr.time.rule`` method built on
        ``hr.time.rule._apply_output`` (``_apply_attendance_output``, ``_apply_leave_output``),
        adding model specific effects such as allocations.

        :param rules: the ``hr.time.rule`` records that were evaluated
        :param dict excess: ``{employee: {source: [_Iv]}}``
        :param dict deficit: ``{employee: {source: [(start, stop, rule)]}}``
        :param dict active_iv: ``{employee: {source: Intervals}}``
        """
        raise NotImplementedError

    def _on_sources_collected(self, sources):
        """Hook called with the sources of a batch before the rules are evaluated on them.

        ``hr_holidays`` reverses the allocation credits previously logged on these sources, so the
        evaluation starts from a clean state.

        :param sources: records of this model
        """
        # overriden in hr_holidays
        pass

    def _get_pipeline_intervals_local(self, schedule):
        """Return the segments of the record that enter the pipeline.

        Default: the whole span. ``hr.leave`` clips absence leaves to the schedule, so nights,
        breaks and days off of a leave do not count.

        :param Intervals schedule: schedule of the employee (naive local)
        :return: list of ``(start, stop)`` naive datetimes in the employee's timezone
        :rtype: list
        """
        self.ensure_one()
        tz = ZoneInfo(self.employee_id.sudo()._get_tz())
        start = self[self._time_rule_span_start_field].replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        stop = self[self._time_rule_span_end_field].replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        return [(start, stop)]

    def _get_source_extra_fields_domain(self):
        """Return the domain a record must match to be a source, e.g. being validated.

        :rtype: list
        """
        return []

    def _undo_time_rules(self):
        """Delete all engine outputs and restore the original (archived) source records.

        walks the full descendant tree so multi-level chains (daily-OT output
        used as a source for weekly-OT) are fully removed before the root is unarchived.
        """
        all_outputs = self.browse()
        frontier = self.with_context(active_test=False)
        while frontier:
            children = self.with_context(active_test=False).sudo().search(
                [(self._time_rule_source_field, 'in', frontier.ids)]
            )
            all_outputs |= children
            frontier = children - all_outputs  # avoid infinite loops on unexpected cycles
        all_outputs.with_context(skip_time_rules=True).unlink()
        to_restore = self.with_context(active_test=False).filtered(lambda r: not r.active)
        if to_restore:
            to_restore.write({'active': True})
            to_restore._on_time_rule_undo_restored()

    def _on_time_rule_undo_restored(self):
        """Hook called after archived sources are reactivated by _undo_time_rules."""

    def _get_orphaned_sources_on_unlink(self):
        """returns archived source records that have no other outputs than self"""
        if not self._time_rule_source_field:
            return self.browse()
        children = self.with_context(active_test=False).filtered(
            lambda r: r[self._time_rule_source_field]
        )
        if not children:
            return self.browse()
        sources = children.with_context(active_test=False).mapped(self._time_rule_source_field)
        sources = sources.filtered(lambda s: not s.active)
        if not sources:
            return self.browse()
        deleting_ids = set(self.ids)
        orphaned = self.browse()
        for source in sources:
            siblings = self.with_context(active_test=False).search(
                [(self._time_rule_source_field, '=', source.id)]
            )
            if all(c.id in deleting_ids for c in siblings):
                orphaned |= source
        return orphaned

    def _get_write_source_extra_source_fields(self):
        """Return the fields, besides the employee and the span, whose write triggers the rules.

        :rtype: set[str]
        """
        return set()

    def _get_time_rule_break_hours(self):
        """Return the break hours of the record, not counted as worked time by the rules.

        :rtype: float
        """
        return 0.0

    def _get_time_rule_deficit_occupied(self, employee_id, start_utc, period_end_utc):
        """Return the time already occupied by records of the employee; must be implemented.

        Deficit outputs are only placed in the free slots of ``[start_utc, period_end_utc]``.

        :param int employee_id: employee id
        :param datetime start_utc: naive UTC
        :param datetime period_end_utc: naive UTC
        :return: intervals of naive UTC datetimes
        :rtype: Intervals
        """
        raise NotImplementedError

    def _get_time_rule_deficit_already_covered(self, rule, start_utc, end_utc):
        """Return the hours already covered by outputs of the rule's type in ``[start_utc, end_utc]``.

        Makes deficit outputs idempotent: the hours placed by a previous run are deducted, so
        no duplicate records are created.

        :param rule: the ``hr.time.rule``
        :param datetime start_utc: naive UTC
        :param datetime end_utc: naive UTC
        :rtype: float
        """
        if not rule.work_entry_type_id:
            return 0.0
        dummy = self.env['resource.calendar']
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('work_entry_type_id', '=', rule.work_entry_type_id.id),
            ('time_rule_id', '!=', False),
            (self._time_rule_span_start_field, '<', end_utc),
            (self._time_rule_span_end_field, '>', start_utc),
        ]
        domain.extend(self._get_source_extra_fields_domain())
        existing = self.env[self._name].sudo().search(domain)
        if not existing:
            return 0.0
        window = Intervals([(start_utc, end_utc, dummy)])
        existing_iv = Intervals([
            (r[self._time_rule_span_start_field], r[self._time_rule_span_end_field], dummy)
            for r in existing
        ])
        return sum_intervals(existing_iv & window)

    def _get_time_rule_output_vals(self, rule, df, dt, pp):
        """Return the creation values of an output record of ``rule``; must be implemented.

        :param rule: the ``hr.time.rule`` producing the output
        :param datetime df: start, naive UTC
        :param datetime dt: end, naive UTC
        :param frozenset pp: premium pay ids
        :return: values with at least the employee, the span, the rule's type, ``time_rule_id``
            and the link to the source
        :rtype: dict
        """
        raise NotImplementedError

    def _get_time_rule_remainder_vals(self, df, dt):
        """Return the creation values of a remainder record; must be implemented.

        A remainder is a part of the source not covered by any output, when the source is cut.
        ``work_entry_type_id`` must be left out: the caller sets the source's original type.

        :param datetime df: start, naive UTC
        :param datetime dt: end, naive UTC
        :rtype: dict
        """
        raise NotImplementedError

    def _get_source_records_for_time_rules(self, start_dt, end_dt, employees=None, check_end=False):
        domain = [
            (self._time_rule_span_end_field, '>=', start_dt.replace(tzinfo=None)),
            (self._time_rule_span_end_field, '!=', False),
        ]
        domain.extend(self._get_source_extra_fields_domain())
        if check_end:
            domain.append(
                (self._time_rule_span_end_field, '<=', end_dt.replace(tzinfo=None)))
        else:
            domain.append(
                (self._time_rule_span_start_field, '<', end_dt.replace(tzinfo=None)))
        if employees:
            assert 'employee_id' in self._fields
            domain.append(('employee_id', 'in', employees.ids))
        return self.sudo().search(domain)

    def _merge_rule_outputs(self, a, b):
        merged = defaultdict(lambda: defaultdict(list))
        for outputs in (a, b):
            for emp, by_record in outputs.items():
                for record, items in by_record.items():
                    merged[emp][record].extend(items)
        return merged

    def _merge_active_iv(self, a, b):
        merged = defaultdict(lambda: defaultdict(Intervals))
        for active_iv in (a, b):
            for emp, by_src in active_iv.items():
                for src, iv in by_src.items():
                    merged[emp][src] |= iv
        return merged

    def _collect_time_rule_outputs(self, rules, ranges_by_employee):
        """Evaluate ``rules`` on the sources of each employee's date range; nothing is written.

        Employees sharing the same range are evaluated in one ``_evaluate_rules`` call, after
        :meth:`_on_sources_collected`.

        :param rules: ``hr.time.rule`` records
        :param dict ranges_by_employee: ``{employee: (date_from, date_to)}``, dates in the
            employee's timezone
        :return: merged ``(excess, deficit, active_iv)``, see ``hr.time.rule._evaluate_rules``
        :rtype: tuple
        """
        all_excess = defaultdict(lambda: defaultdict(list))
        all_deficit = defaultdict(lambda: defaultdict(list))
        all_active_iv = defaultdict(lambda: defaultdict(Intervals))
        if not rules:
            return all_excess, all_deficit, all_active_iv

        by_range = defaultdict(list)
        for employee, (date_from, date_to) in ranges_by_employee.items():
            by_range[date_from, date_to].append(employee)

        for (date_from, date_to), employees in by_range.items():
            # naive local bounds of the evaluated days, the end excluded
            start_dt = datetime.combine(date_from, time.min)
            end_dt = datetime.combine(date_to + timedelta(days=1), time.min)
            employee_rs = self.env['hr.employee'].browse([e.id for e in employees])

            sources = self.sudo().browse()
            for tz, tz_employees in employee_rs.grouped(lambda e: e.sudo()._get_tz()).items():
                tzinfo = ZoneInfo(tz)
                sources |= self._get_source_records_for_time_rules(
                    start_dt.replace(tzinfo=tzinfo).astimezone(UTC),
                    end_dt.replace(tzinfo=tzinfo).astimezone(UTC),
                    tz_employees,
                )
            if not sources:
                continue

            self._on_sources_collected(sources)
            excess, deficit, active_iv = rules._evaluate_rules(sources, start_dt, end_dt)

            for emp, by_src in excess.items():
                for src, items in by_src.items():
                    all_excess[emp][src].extend(items)
            for emp, by_src in deficit.items():
                for src, items in by_src.items():
                    all_deficit[emp][src].extend(items)
            for emp, by_src in active_iv.items():
                for src, iv in by_src.items():
                    all_active_iv[emp][src] |= iv

        return all_excess, all_deficit, all_active_iv

    @api.model
    def _cron_process_day_undertime_rules(self):
        """Cron: evaluate the daily ``less_than`` (undertime) rules on yesterday's records.

        Undertime of the current day cannot be known while the day runs, so it is not
        evaluated on write. A day without any source record produces no deficit.
        """
        assert 'employee_id' in self._fields
        yesterday = date.today() - timedelta(days=1)
        start = datetime.combine(yesterday, time.min)
        end = datetime.combine(yesterday, time.max)
        sources = self._get_source_records_for_time_rules(start, end, check_end=True)
        if not sources:
            return
        affected = [(s.employee_id, s[s._time_rule_span_start_field], s[s._time_rule_span_end_field]) for s in sources]
        self._process_time_rules_for(affected, rule_period='day', rule_operator='less_than')

    @api.model
    def _cron_process_week_time_rules(self):
        """Cron: evaluate the weekly rules (both operators) on the week that ended yesterday.

        On day X, yesterday was the last day of every week starting on X: only the rules whose
        ``week_start`` is X are processed, on the records ending in ``[X-7, X-1]``. This assumes a
        daily run.
        """
        assert 'employee_id' in self._fields
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_start_key = str(today.weekday())   # '0'=Mon … '6'=Sun
        week_end = yesterday
        week_start_date = week_end - timedelta(days=6)
        start = datetime.combine(week_start_date, time.min)
        end = datetime.combine(week_end, time.max)
        sources = self._get_source_records_for_time_rules(start, end, check_end=True)
        if not sources:
            return
        affected = [(s.employee_id, s[s._time_rule_span_start_field], s[s._time_rule_span_end_field]) for s in sources]
        self._process_time_rules_for(affected, rule_period='week', rule_week_start=week_start_key)

    def _process_time_rules_for(self, affected, rule_period=None, rule_operator=None, rule_week_start=None):
        """Evaluate and apply the active rules for the given employees and periods.

        Rules are those of the current companies (or without company), filtered by
        ``rule_operator`` and period. Daily rules are evaluated on each employee's covering date
        range, weekly rules on that range widened to whole weeks; both results are applied
        together through :meth:`_apply_record_output`.

        :param list affected: ``(employee, date_from, date_to)`` tuples: dates in the employee's
            timezone, or UTC datetimes (naive or aware), evaluated on their dates in the
            employee's timezone
        :param str rule_period: ``'day'`` or ``'week'`` to only process that kind of rule;
            both if ``None``
        :param str rule_operator: ``'exceed'`` or ``'less_than'`` to only process that operator
        :param str rule_week_start: only process the weekly rules with this ``week_start``
        """
        if not affected:
            return

        rules = self.env['hr.time.rule'].sudo().search([
            ('active', '=', True),
            '|',
                ('company_id', '=', False),
                ('company_id', 'in', self.env.companies.ids),
        ])
        if not rules:
            return

        if rule_operator:
            rules = rules.filtered(lambda r: r.threshold_operator == rule_operator)

        if rule_period == 'day':
            day_rules = rules.filtered(lambda r: r.quantity_period != 'week')
            week_rules = rules.browse()
        elif rule_period == 'week':
            day_rules = rules.browse()
            week_rules = rules.filtered(lambda r: r.quantity_period == 'week')
        else:
            day_rules = rules.filtered(lambda r: r.quantity_period != 'week')
            week_rules = rules.filtered(lambda r: r.quantity_period == 'week')

        if rule_week_start is not None:
            week_rules = week_rules.filtered(lambda r: (r.week_start or '0') == rule_week_start)

        if not day_rules and not week_rules:
            return

        day_rules_ranges = defaultdict(lambda: [None, None])
        for employee, date_from, date_to in affected:
            df = _to_local_date(employee, date_from)
            dt = _to_local_date(employee, date_to)
            r = day_rules_ranges[employee]
            r[0] = df if r[0] is None else min(r[0], df)
            r[1] = dt if r[1] is None else max(r[1], dt)

        weekly_starts = {int(r.week_start or '0') for r in week_rules}
        week_rules_ranges = {}
        if weekly_starts:
            for employee, (df, dt) in day_rules_ranges.items():
                wdf, wdt = df, dt
                for ws in weekly_starts:
                    wdf = min(wdf, wdf - relativedelta(days=(wdf.weekday() - ws) % 7))
                    wdt = max(wdt, wdt + relativedelta(days=(ws - 1 - wdt.weekday()) % 7))
                week_rules_ranges[employee] = (wdf, wdt)

        day_excess, day_deficit, day_active_iv = self._collect_time_rule_outputs(day_rules, day_rules_ranges)
        week_excess, week_deficit, week_active_iv = self._collect_time_rule_outputs(week_rules, week_rules_ranges)

        merged_excess = self._merge_rule_outputs(day_excess, week_excess)
        merged_deficit = self._merge_rule_outputs(day_deficit, week_deficit)
        merged_active_iv = self._merge_active_iv(day_active_iv, week_active_iv)
        self._apply_record_output(day_rules | week_rules, merged_excess, merged_deficit, merged_active_iv)

    def _trigger_time_rules(self, include_deficit=False):
        """Apply the full day/week, past/current, exceed/undertime split for validated source record."""
        domain = [
            (self._time_rule_span_start_field, '!=', False),
            (self._time_rule_span_end_field, '!=', False),
        ]
        domain.extend(self._get_source_extra_fields_domain())
        domain.append(('time_rule_id', '=', False))
        validated = self.filtered_domain(domain)
        if not validated:
            return
        assert 'employee_id' in self._fields
        names = [r.sudo().display_name for r in validated[:3]]
        if len(validated) > 3:
            names.append(self.env._('… and %d more', len(validated) - 3))
        self.with_context(
            time_rule_trigger_model=self._name,
            time_rule_trigger_desc=', '.join(names),
        )._trigger_time_rules_for_affected(
            [(r.employee_id, r[r._time_rule_span_start_field], r[r._time_rule_span_end_field]) for r in validated],
            include_deficit=include_deficit,
        )

    def _trigger_time_rules_for_affected(self, affected, include_deficit=False):
        """
        include_deficit: when True also evaluates less_than (undertime) day rules, which are
        normally cron-only.
        """
        if not affected:
            return
        today = date.today()

        # find the earliest active week-rule week-start to use as the current-week boundary;
        # using min across all rules ensures a record inside ANY rule's current week is deferred
        week_rules = self.env['hr.time.rule'].sudo().search([
            ('active', '=', True),
            ('quantity_period', '=', 'week'),
            '|', ('company_id', '=', False), ('company_id', 'in', self.env.companies.ids),
        ])
        if week_rules:
            week_starts = {int(r.week_start or '0') for r in week_rules}
            latest_week_start = min(
                today - timedelta(days=(today.weekday() - ws) % 7)
                for ws in week_starts
            )
        else:
            latest_week_start = today - timedelta(days=today.weekday())

        past_day = [(e, df, dt) for e, df, dt in affected if _to_local_date(e, dt) < today]
        today_list = [(e, df, dt) for e, df, dt in affected if _to_local_date(e, dt) >= today]
        past_week = [(e, df, dt) for e, df, dt in affected if _to_local_date(e, dt) < latest_week_start]
        ctx = self.with_context(time_rule_reversed_ids=set())
        ctx._process_time_rules_for(past_day, rule_period='day', rule_operator='exceed')
        if include_deficit:
            ctx._process_time_rules_for(past_day, rule_period='day', rule_operator='less_than')
        ctx._process_time_rules_for(today_list, rule_period='day', rule_operator='exceed')
        ctx._process_time_rules_for(past_week, rule_period='week', rule_operator='exceed')

    def write(self, vals):
        assert 'employee_id' in self._fields
        res = super().write(vals)
        trigger_fields = {'employee_id', self._time_rule_span_start_field, self._time_rule_span_end_field} | self._get_write_source_extra_source_fields()
        if not self.env.context.get('skip_time_rules') and trigger_fields.intersection(vals):
            self._trigger_time_rules()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if not self.env.context.get('skip_time_rules'):
            res._trigger_time_rules()
        return res
