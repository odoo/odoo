# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime, time, timedelta, UTC

from odoo import api, models


def _max_span_end(children, src_field, start_field, end_field):
    result = {}
    for child in children:
        src = child[src_field]
        if not src:
            continue
        if child[start_field] > src[end_field]:
            continue  # deficit child extends past source end
        child_end = child[end_field]
        if child_end and (src.id not in result or child_end > result[src.id]):
            result[src.id] = child_end
    return result


class HrTimeRuleSourceMixin(models.AbstractModel):
    """Mixin for hr.attendance and hr.leave models to support time rule evaluation."""

    _name = 'hr.time.rule.source.mixin'
    _description = 'Time Rule Source Mixin'

    # subclasses declare these
    _time_rule_source_field = ''      # m2o from output to source
    _time_rule_output_field = ''      # o2m from source to output
    _time_rule_span_start_field = ''  # span start field name
    _time_rule_span_end_field = ''    # span end field name

    def _apply_record_output(self, excess, deficit):
        raise NotImplementedError

    def _get_source_extra_fields_domain(self):
        return []

    def _get_write_source_extra_source_fields(self):
        return {}

    def _get_source_records_for_time_rules(self, start_dt, end_dt, employees=None, check_end=False):
        domain = [
            (self._time_rule_source_field, '=', False),
            (self._time_rule_span_end_field, '>=', start_dt.replace(tzinfo=None)),
            (self._time_rule_span_end_field, '!=', False),
        ]
        domain.extend(self._get_source_extra_fields_domain())
        if check_end:
            domain.append(
                (self._time_rule_span_end_field, '<=', end_dt.replace(tzinfo=None)))
        else:
            domain.append(
                (self._time_rule_span_start_field, '<=', end_dt.replace(tzinfo=None)))
        if employees:
            assert 'employee_id' in self._fields
            domain.append(('employee_id', 'in', employees.ids))
        return self.sudo().with_context(active_test=False).search(domain)

    def _collect_auto_ctx(self):
        """Context dict used for internal writes during collection."""
        return dict(skip_time_rules=True, tracking_disable=True)

    def _restore_source_span(self, source, original_end, auto_ctx):
        """Write original_end back as the span-end field of source."""
        source.with_context(**auto_ctx).write({
            'active': True,
            self._time_rule_span_end_field: original_end,
        })

    def _after_source_restore(self, modified_sources, auto_ctx):
        """Called after span restoration; override for model-specific side effects."""

    def _merge_rule_outputs(self, a, b):
        merged = defaultdict(lambda: defaultdict(list))
        for outputs in (a, b):
            for emp, by_record in outputs.items():
                for record, items in by_record.items():
                    merged[emp][record].extend(items)
        return merged

    def _collect_time_rule_outputs(self, rules, ranges_by_employee):
        all_excess = defaultdict(lambda: defaultdict(list))
        all_deficit = defaultdict(lambda: defaultdict(list))
        if not rules:
            return all_excess, all_deficit

        by_range = defaultdict(list)
        for employee, (date_from, date_to) in ranges_by_employee.items():
            start_dt = datetime.combine(date_from, time.min).replace(tzinfo=UTC)
            end_dt = datetime.combine(date_to, time.max).replace(tzinfo=UTC)
            by_range[start_dt, end_dt].append(employee)

        auto_ctx = self._collect_auto_ctx()
        src_field = self._time_rule_source_field
        start_field = self._time_rule_span_start_field
        end_field = self._time_rule_span_end_field

        for (start_dt, end_dt), employees in by_range.items():
            employee_rs = self.env['hr.employee'].browse([e.id for e in employees])
            sources = self._get_source_records_for_time_rules(start_dt, end_dt, employee_rs)
            if not sources:
                continue

            is_weekly = bool(rules) and all(r.quantity_period == 'week' for r in rules)
            all_children = self.sudo().search([(src_field, 'in', sources.ids)])

            if is_weekly:
                # only delete prior weekly-rule outputs; day-rule outputs must be preserved
                non_weekly = all_children.filtered(lambda c: c.time_rule_id not in rules)
                (all_children - non_weekly).with_context(skip_time_rules=True).unlink()
                span_end_by_src = _max_span_end(non_weekly, src_field, start_field, end_field)
            else:
                # skip restore when caller explicitly wrote a new span-end (don't override intent)
                from_write = self.env.context.get('source_bounds_from_write')
                span_end_by_src = (
                    {} if from_write
                    else _max_span_end(all_children, src_field, start_field, end_field)
                )
                all_children.with_context(skip_time_rules=True).unlink()

            modified_sources = self.browse()
            for src in sources:
                src_end = src[end_field]
                original_end = max(src_end, span_end_by_src.get(src.id, src_end))
                if not src.active or original_end != src_end:
                    self._restore_source_span(src, original_end, auto_ctx)
                    modified_sources |= src

            self._after_source_restore(modified_sources, auto_ctx)

            excess, deficit = rules._evaluate_rules(sources, start_dt, end_dt)

            for emp, by_src in excess.items():
                for src, items in by_src.items():
                    all_excess[emp][src].extend(items)
            for emp, by_src in deficit.items():
                for src, items in by_src.items():
                    all_deficit[emp][src].extend(items)

        return all_excess, all_deficit

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
        """Weekly cron: process week-based time rules for the Mon-Sun that just ended."""
        assert 'employee_id' in self._fields
        today = date.today()
        week_end = today - timedelta(days=1)
        week_start = week_end - timedelta(days=6)
        start = datetime.combine(week_start, time.min)
        end = datetime.combine(week_end, time.max)
        sources = self._get_source_records_for_time_rules(start, end, check_end=True)
        if not sources:
            return
        affected = [(s.employee_id, s[s._time_rule_span_start_field], s[s._time_rule_span_end_field]) for s in sources]
        self._process_time_rules_for(affected, rule_period='week')

    def _process_time_rules_for(self, affected, rule_period=None, rule_operator=None):
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

        day_excess, day_deficit = self._collect_time_rule_outputs(day_rules, day_rules_ranges)
        week_excess, week_deficit = self._collect_time_rule_outputs(week_rules, week_rules_ranges)

        merged_excess = self._merge_rule_outputs(day_excess, week_excess)
        merged_deficit = self._merge_rule_outputs(day_deficit, week_deficit)
        self._apply_record_output(day_rules | week_rules, merged_excess, merged_deficit)

    def _trigger_time_rules(self):
        """Apply the full day/week, past/current, exceed/undertime split for validated source record."""
        domain = [
            (self._time_rule_span_start_field, '!=', False),
            (self._time_rule_span_end_field, '!=', False),
        ]
        domain.extend(self._get_source_extra_fields_domain())
        validated = self.filtered_domain(domain)
        if not validated:
            return
        assert 'employee_id' in self._fields
        self._trigger_time_rules_for_affected([(r.employee_id, r[r._time_rule_span_start_field], r[r._time_rule_span_end_field]) for r in validated])

    def _trigger_time_rules_for_affected(self, affected):
        """Apply day/week, past/current, exceed/undertime split for (employee, date_from, date_to) tuples."""
        if not affected:
            return
        today = date.today()
        latest_monday = today - timedelta(days=today.weekday())

        def to_date(dt):
            return dt.date() if hasattr(dt, 'date') else dt
        past_day = [(e, df, dt) for e, df, dt in affected if to_date(dt) < today]
        today = [(e, df, dt) for e, df, dt in affected if to_date(dt) >= today]
        past_week = [(e, df, dt) for e, df, dt in affected if to_date(dt) < latest_monday]
        self._process_time_rules_for(past_day, rule_period='day')
        self._process_time_rules_for(today, rule_period='day', rule_operator='exceed')
        self._process_time_rules_for(past_week, rule_period='week')

    def write(self, vals):
        assert 'employee_id' in self._fields
        res = super().write(vals)
        trigger_fields = {'employee_id', self._time_rule_span_start_field, self._time_rule_span_end_field} | self._get_write_source_extra_source_fields()
        if not self.env.context.get('skip_time_rules') and trigger_fields.intersection(vals):
            self._trigger_time_rules()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_output_leaves(self):
        self.sudo().mapped(self._time_rule_output_field).with_context(skip_time_rules=True).unlink()

    def unlink(self):
        # capture affected info before records are deleted, for the post-deletion recompute
        if not self.env.context.get('skip_time_rules'):
            assert 'employee_id' in self._fields
            domain = [
                (self._time_rule_span_start_field, '!=', False),
                (self._time_rule_span_end_field, '!=', False),
            ]
            domain.extend(self._get_source_extra_fields_domain())
            validated = self.filtered_domain(domain)
            affected = [(r.employee_id, r[r._time_rule_span_start_field], r[r._time_rule_span_end_field]) for r in validated]
        res = super().unlink()
        if not self.env.context.get('skip_time_rules') and affected:
            self._trigger_time_rules_for_affected(affected)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if not self.env.context.get('skip_time_rules'):
            res._trigger_time_rules()
        return res
