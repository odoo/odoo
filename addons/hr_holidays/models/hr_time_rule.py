# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, date
from zoneinfo import ZoneInfo

from odoo import api, fields, models


class HrTimeRuleSourceMixin(models.AbstractModel):
    _inherit = 'hr.time.rule.source.mixin'

    def _on_sources_collected(self, sources):
        """Reverse prior allocation credits before the batch is re-evaluated.

        - child outputs and sources are reversed so the pipeline can recompute from scratch.
        - in-place outputs (time_rule_id set, no source pointer) keep their credit
          because the evaluation will not reclassify them.

        :param sources: records of the source model
        """
        reversed_ids = self.env.context.get('time_rule_reversed_ids')
        source_field = sources._time_rule_source_field
        to_reverse = set(sources.filtered(lambda s: not s.time_rule_id or s[source_field]).ids)
        if reversed_ids is not None:
            to_reverse -= reversed_ids
            reversed_ids |= to_reverse
        if to_reverse:
            self.env['hr.time.rule']._reverse_allocation_credits(self._name, to_reverse)


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    work_entry_type_id = fields.Many2one(
        domain="[('id', 'in', country_work_entry_type_ids), ('requires_allocation', '=', False)]",
    )

    leave_compensation_rate = fields.Float(
        "Allocate %",
        default=0.0,
        help="Leave allocated or taken at this rate of the excess or deficit. 100% = 1:1.",
    )
    allocation_type_id = fields.Many2one(
        'hr.work.entry.type',
        string="Allocate to",
        domain="[('requires_allocation', '=', True), ('time_off_selectable', '=', True), ('id', 'in', country_work_entry_type_ids)]",
    )

    def _resolve_output_intervals(self, intervals):
        """Resolve the output intervals, then merge consecutive slices with the same merge key.

        See :meth:`_get_output_leave_merge_key`.

        :rtype: list
        """
        resolved = super()._resolve_output_intervals(intervals)
        merged = []
        for iv in resolved:
            mk = iv.rule._get_output_leave_merge_key(accumulated_pp=iv.pp)
            if merged and merged[-1][0].end == iv.start and merged[-1][1] == mk:
                prev, _ = merged[-1]
                merged[-1] = (prev._replace(end=iv.end, pp=prev.pp | iv.pp), mk)
            else:
                merged.append((iv, mk))
        return [iv for iv, _mk in merged]

    def _get_output_leave_vals(self, employee, rule, date_from, date_to, source_leave, accumulated_pp=frozenset()):
        """Return the creation values of a validated time off output by ``rule``.

        The output has the rule's type, ``time_rule_id``, the given span and is linked to
        ``source_leave``.

        :param employee: ``hr.employee``
        :param rule: ``hr.time.rule`` producing the output
        :param datetime date_from: start, naive UTC
        :param datetime date_to: end, naive UTC
        :param source_leave: source ``hr.leave``
        :param frozenset accumulated_pp: premium pay ids
        :rtype: dict
        """
        tz = ZoneInfo(employee._get_tz())
        df_local = date_from.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        dt_local = date_to.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        return {
            'employee_id': employee.id,
            'work_entry_type_id': rule.work_entry_type_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': df_local.date(),
            'request_date_to': dt_local.date(),
            'request_hour_from': df_local.hour + df_local.minute / 60,
            'request_hour_to': dt_local.hour + dt_local.minute / 60,
            'time_rule_id': rule.id,
            'source_leave_id': source_leave.id,
            'resource_calendar_id': source_leave.resource_calendar_id.id,
            'state': 'validate',
        }

    def _get_output_leave_merge_key(self, accumulated_pp=frozenset()):
        """Return the hashable key deciding when consecutive excess slices make one time off.

        Override to add discriminators (e.g. the premium pays in Belgium). Default: the rule.
        """
        return self

    def _apply_allocation_credits(self, excess_alloc, deficit_alloc, *, approve_ctx=None):
        """Credit (or deduct) the excess (or missing) hours of rules to allocations, and log it.

        For rules with ``leave_compensation_rate`` and ``allocation_type_id``, the excess or deficit hours
        are added to (or deducted from) the employee validated allocations

        excess credits go to an open-ended allocation (or a new one is created).
        deficit deducts from earliest-expiring validated allocations first.

        :param list excess_alloc: ``[employee, rule, hours, source, log_source]`` rows
        :param list deficit_alloc: same rows for the deficits
        :param dict approve_ctx: context to approve the created allocations with
        """
        approve_ctx = approve_ctx or {}

        # pre-fetch version-aware hours_per_day for all (employee, source_date) pairs
        emps_by_date = defaultdict(lambda: self.env['hr.employee'])
        for employee, rule, _hours, source, _log in (*excess_alloc, *deficit_alloc):
            if rule.leave_compensation_rate > 0 and rule.allocation_type_id:
                dt = source[source._time_rule_span_start_field]
                emps_by_date[dt.date() if hasattr(dt, 'date') else dt] |= employee
        hours_per_day_cache = {}
        for source_date, employees in emps_by_date.items():
            for emp_id, hours_per_day in employees._get_hours_per_day_batch(source_date).items():
                hours_per_day_cache[emp_id, source_date] = hours_per_day or 8.0

        excess_by_key = defaultdict(float)
        log_by_source = defaultdict(float)
        earliest_date_by_key = {}

        for employee, rule, excess_hours, source, log_source in excess_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            dt = source[source._time_rule_span_start_field]
            source_date = dt.date() if hasattr(dt, 'date') else dt
            hours_per_day = hours_per_day_cache[employee.id, source_date]
            alloc_days = excess_hours * rule.leave_compensation_rate / hours_per_day
            if alloc_days > 0:
                key = (employee, rule.allocation_type_id)
                excess_by_key[key] += alloc_days
                log_by_source[log_source._name, log_source.id, employee, rule.allocation_type_id] += alloc_days
                if key not in earliest_date_by_key or source_date < earliest_date_by_key[key]:
                    earliest_date_by_key[key] = source_date

        deficit_by_key = defaultdict(float)
        for employee, rule, deficit_hours, source, log_source in deficit_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            dt = source[source._time_rule_span_start_field]
            source_date = dt.date() if hasattr(dt, 'date') else dt
            hours_per_day = hours_per_day_cache[employee.id, source_date]
            deduct = deficit_hours * rule.leave_compensation_rate / hours_per_day
            if deduct > 0:
                key = (employee, rule.allocation_type_id)
                deficit_by_key[key] += deduct
                log_by_source[log_source._name, log_source.id, employee, rule.allocation_type_id] -= deduct
                if key not in earliest_date_by_key or source_date < earliest_date_by_key[key]:
                    earliest_date_by_key[key] = source_date

        all_keys = set(excess_by_key) | set(deficit_by_key)
        if not all_keys:
            return

        Alloc = self.env['hr.leave.allocation'].sudo()
        alloc_cache = {key: Alloc for key in all_keys}
        for employee, alloc_type, allocs in Alloc.with_context(active_test=False)._read_group(
            [('employee_id', 'in', [e.id for e, _ in all_keys]),
             ('work_entry_type_id', 'in', [t.id for _, t in all_keys]),
             ('state', '=', 'validate')],
            groupby=['employee_id', 'work_entry_type_id'],
            aggregates=['id:recordset'],
        ):
            key = (employee, alloc_type)
            if key in alloc_cache:
                alloc_cache[key] = allocs.sorted(key=lambda a: (a.date_to or date.max,))

        alloc_by_key = {}
        alloc_create_vals = []
        alloc_create_keys = []
        for (employee, alloc_type), alloc_days in excess_by_key.items():
            open_ended = [a for a in alloc_cache.get((employee, alloc_type), []) if not a.date_to]
            if open_ended:
                open_ended[0].with_context(time_rule_deduction=True).number_of_days += alloc_days
                alloc_by_key[employee, alloc_type] = open_ended[0]
            else:
                alloc_create_vals.append({
                    'employee_id': employee.id,
                    'work_entry_type_id': alloc_type.id,
                    'number_of_days': alloc_days,
                    'date_from': earliest_date_by_key.get((employee, alloc_type)),
                    'date_to': False,
                    'state': 'confirm',
                })
                alloc_create_keys.append((employee, alloc_type))
        if alloc_create_vals:
            new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True, time_rule_deduction=True).create(alloc_create_vals)
            new_allocs.with_context(time_rule_deduction=True, **approve_ctx).action_approve()
            for key, alloc in zip(alloc_create_keys, new_allocs):
                alloc_by_key[key] = alloc

        deficit_create_vals = []
        deficit_create_keys = []
        for (employee, alloc_type), deduct in deficit_by_key.items():
            allocations = alloc_cache.get((employee, alloc_type), self.env['hr.leave.allocation'])
            if allocations:
                allocations[-1].with_context(time_rule_deduction=True).number_of_days -= deduct
                alloc_by_key.setdefault((employee, alloc_type), allocations[-1])
            else:
                deficit_create_vals.append({
                    'employee_id': employee.id,
                    'work_entry_type_id': alloc_type.id,
                    'number_of_days': -deduct,
                    'date_from': earliest_date_by_key.get((employee, alloc_type)),
                    'date_to': False,
                    'state': 'confirm',
                })
                deficit_create_keys.append((employee, alloc_type))
        if deficit_create_vals:
            new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True, time_rule_deduction=True).create(deficit_create_vals)
            new_allocs.with_context(time_rule_deduction=True, **approve_ctx).action_approve()
            for key, alloc in zip(deficit_create_keys, new_allocs):
                alloc_by_key[key] = alloc

        log_vals = []
        for (source_model, source_id, employee, alloc_type), days in log_by_source.items():
            allocation = alloc_by_key.get((employee, alloc_type))
            if allocation and days:
                log_vals.append({
                    'res_model': source_model,
                    'res_id': source_id,
                    'allocation_id': allocation.id,
                    'days': days,
                })
        if log_vals:
            self.env['hr.time.rule.allocation.log'].sudo().create(log_vals)

    def _apply_leave_output(self, excess, deficit, active_iv=None):
        """Apply the time rule result on time off sources.

        Creates the outputs (``_apply_output``, defined by ``hr_work_entry``), credits the
        allocations (:meth:`_apply_allocation_credits`) and recreates the resource leaves of the
        sources and outputs.

        :param dict excess: ``{employee: {source: [_Iv]}}``
        :param dict deficit: ``{employee: {source: [(start, stop, rule)]}}``
        :param dict active_iv: ``{employee: {source: Intervals}}``
        """
        new_records, all_source_ids, excess_alloc, deficit_alloc = self._apply_output(excess, deficit, active_iv=active_iv)
        self._apply_allocation_credits(
            excess_alloc, deficit_alloc,
            approve_ctx={'leave_skip_state_check': True},
        )
        if all_source_ids:
            Leave = self.env['hr.leave'].sudo()
            sources = Leave.with_context(active_test=False).browse(list(all_source_ids))
            (sources | new_records).with_context(**Leave._time_rule_write_ctx)._create_resource_leave()

    @api.model
    def _reverse_allocation_credits(self, source_model, source_ids):
        """Reverse the allocation credits logged for the given source records.

        :param str source_model: ``'hr.leave'`` or ``'hr.attendance'``
        :param source_ids: ids of the sources
        """
        if not source_ids:
            return
        Log = self.env['hr.time.rule.allocation.log'].sudo()
        logs = Log.search([
            ('res_model', '=', source_model),
            ('res_id', 'in', list(source_ids)),
        ])
        if not logs:
            return
        by_alloc = defaultdict(float)
        for log in logs:
            by_alloc[log.allocation_id] += log.days
        for allocation, days in by_alloc.items():
            if not allocation.exists() or not days:
                continue
            allocation.with_context(time_rule_deduction=True).number_of_days -= days
        logs.unlink()
