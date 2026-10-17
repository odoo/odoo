# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime, time, timedelta, UTC
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.date_utils import sum_intervals
from odoo.tools.intervals import Intervals


class HrTimeRuleSourceMixin(models.AbstractModel):
    """Mixin for hr.attendance and hr.leave models to support time rule evaluation."""

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
        raise NotImplementedError

    def _on_sources_collected(self, sources):
        # overriden in hr_holidays
        pass

    def _get_pipeline_intervals_local(self, schedule):
        """Return (start, stop) local-naive pairs for this record's pipeline segments.

        Default: one interval for the full raw span.
        Override for multi-day absence leaves, clip to schedule.
        """
        self.ensure_one()
        tz = ZoneInfo(self.employee_id.sudo()._get_tz())
        start = self[self._time_rule_span_start_field].replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        stop = self[self._time_rule_span_end_field].replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        return [(start, stop)]

    def _get_source_extra_fields_domain(self):
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
        self.with_context(active_test=False).write({'active': True})

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
        return set()

    def _get_time_rule_break_hours(self):
        return 0.0

    def _get_time_rule_end_write_vals(self, end_utc, stop_local):
        """Write vals dict for updating the span-end field.

        end_utc is the new UTC end datetime; stop_local is the same instant as a
        naive datetime in the employee's tz.  Leave overrides to also write
        request_date_to / request_hour_to.
        """
        return {self._time_rule_span_end_field: end_utc}

    def _get_time_rule_deficit_occupied(self, employee_id, start_utc, period_end_utc):
        """Return Intervals of existing records that occupy [start_utc, period_end_utc].

        Used by the deficit go-around algorithm to find free slots.
        """
        raise NotImplementedError

    def _get_time_rule_deficit_already_covered(self, rule, start_utc, end_utc):
        """Hours already covered by existing deficit outputs of this rule's WET in [start_utc, end_utc].

        helps make deficit output creation idempotent: if a prior pipeline run already placed
        outputs for this deficit, subsequent runs deduct that coverage from remaining hours
        so no duplicate records are created.
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
        """Create vals for a new time rule output record.

        df/dt are UTC datetimes; pp is a frozenset of premium pay rule IDs.
        """
        raise NotImplementedError

    def _get_time_rule_remainder_vals(self, df, dt):
        """Create vals for a remainder record (source's original type, trimmed span).

        df/dt are UTC datetimes. work_entry_type_id is intentionally omitted;
        the caller fills it with the source's original WET before creating.
        """
        raise NotImplementedError

    def _get_source_records_for_time_rules(self, start_dt, end_dt, employees=None, check_end=False, root_only=True):
        domain = [
            (self._time_rule_span_end_field, '>=', start_dt.replace(tzinfo=None)),
            (self._time_rule_span_end_field, '!=', False),
        ]
        domain.extend(self._get_source_extra_fields_domain())
        if root_only:
            domain.append(('time_rule_id', '=', False))
        if check_end:
            domain.append(
                (self._time_rule_span_end_field, '<=', end_dt.replace(tzinfo=None)))
        else:
            domain.append(
                (self._time_rule_span_start_field, '<=', end_dt.replace(tzinfo=None)))
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

    def _pre_undo_rule_outputs(self, rules, start_dt, end_dt, employees):
        if not self._time_rule_source_field:
            return
        start_naive = start_dt.replace(tzinfo=None)
        end_naive = end_dt.replace(tzinfo=None)
        domain = [
            (self._time_rule_source_field, '!=', False),
            ('time_rule_id', 'in', rules.ids),
            (self._time_rule_span_start_field, '<=', end_naive),
            (self._time_rule_span_end_field, '>=', start_naive),
        ]
        if employees:
            domain.append(('employee_id', 'in', employees.ids))
        outputs = self.with_context(active_test=False).sudo().search(domain)
        if outputs:
            sources = outputs.mapped(self._time_rule_source_field)
            sources.with_context(active_test=False)._undo_time_rules()

    def _collect_time_rule_outputs(self, rules, ranges_by_employee):
        all_excess = defaultdict(lambda: defaultdict(list))
        all_deficit = defaultdict(lambda: defaultdict(list))
        all_active_iv = defaultdict(lambda: defaultdict(Intervals))
        if not rules:
            return all_excess, all_deficit, all_active_iv

        by_range = defaultdict(list)
        for employee, (date_from, date_to) in ranges_by_employee.items():
            start_dt = datetime.combine(date_from, time.min).replace(tzinfo=UTC)
            end_dt = datetime.combine(date_to, time.max).replace(tzinfo=UTC)
            by_range[start_dt, end_dt].append(employee)

        for (start_dt, end_dt), employees in by_range.items():
            employee_rs = self.env['hr.employee'].browse([e.id for e in employees])

            self._pre_undo_rule_outputs(rules, start_dt, end_dt, employee_rs)

            sources = self._get_source_records_for_time_rules(start_dt, end_dt, employee_rs, root_only=False)
            if not sources:
                continue

            # _pre_undo may un-archive a source that falls outside [start_dt, end_dt];
            # extend the eval window so all its days are re-evaluated
            start_field = sources._time_rule_span_start_field
            end_field = sources._time_rule_span_end_field
            earliest = min((r[start_field] for r in sources if r[start_field]), default=None)
            latest = max((r[end_field] for r in sources if r[end_field]), default=None)
            eval_start = min(start_dt, datetime.combine(earliest.date(), time.min, tzinfo=UTC)) if earliest else start_dt
            eval_end = max(end_dt, datetime.combine(latest.date(), time.max, tzinfo=UTC)) if latest else end_dt

            self._on_sources_collected(sources)
            excess, deficit, active_iv = rules._evaluate_rules(sources, eval_start, eval_end)

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
        """Daily cron: process day-based time rules for yesterday's records."""
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
        """Daily cron: process week rules whose week boundary fell on yesterday.

        On day X, yesterday was the last day of every week that starts on X.
        Only rules with week_start matching X are processed, using the 7-day
        window [X-7 .. X-1].  Days with no matching rules are a cheap no-op.
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
        """Recompute time rule outputs for the given (employee, date_from, date_to) tuples.
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
            df = date_from.date() if hasattr(date_from, 'date') else date_from
            dt = date_to.date() if hasattr(date_to, 'date') else date_to
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

        def to_date(dt):
            return dt.date() if hasattr(dt, 'date') else dt
        past_day = [(e, df, dt) for e, df, dt in affected if to_date(dt) < today]
        today_list = [(e, df, dt) for e, df, dt in affected if to_date(dt) >= today]
        past_week = [(e, df, dt) for e, df, dt in affected if to_date(dt) < latest_week_start]
        # deficit (undertime) rules are cron-only by default
        self._process_time_rules_for(past_day, rule_period='day', rule_operator='exceed')
        if include_deficit:
            self._process_time_rules_for(past_day, rule_period='day', rule_operator='less_than')
        self._process_time_rules_for(today_list, rule_period='day', rule_operator='exceed')
        self._process_time_rules_for(past_week, rule_period='week', rule_operator='exceed')

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
