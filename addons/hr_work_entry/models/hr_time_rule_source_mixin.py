# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, datetime, time

from odoo import models


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
    _time_rule_span_start_field = ''  # span start field name
    _time_rule_span_end_field = ''    # span end field name

    def _get_source_records_for_time_rules(self, employees, start_dt, end_dt):
        """Return validated source records overlapping [start_dt, end_dt] for employees."""
        raise NotImplementedError

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
            sources = self._get_source_records_for_time_rules(employee_rs, start_dt, end_dt)
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
