# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrTimeRuleSourceMixin(models.AbstractModel):
    _inherit = 'hr.time.rule.source.mixin'

    def _on_sources_collected(self, sources):
        """Reverse prior allocation credits before the batch is re-evaluated.

        :param sources: records of the source model
        """
        reversed_ids = self.env.context.get('time_rule_reversed_ids')
        to_reverse = set(sources.ids)
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
        hpd_cache = {}
        for source_date, employees in emps_by_date.items():
            for emp_id, hpd in employees._get_hours_per_day_batch(source_date).items():
                hpd_cache[emp_id, source_date] = hpd or 8.0

        excess_by_key = defaultdict(float)
        log_by_source = defaultdict(float)

        for employee, rule, excess_hours, source, log_source in excess_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            dt = source[source._time_rule_span_start_field]
            hours_per_day = hpd_cache[employee.id, dt.date() if hasattr(dt, 'date') else dt]
            alloc_days = excess_hours * rule.leave_compensation_rate / hours_per_day
            if alloc_days > 0:
                excess_by_key[employee, rule.allocation_type_id] += alloc_days
                log_by_source[log_source._name, log_source.id, employee, rule.allocation_type_id] += alloc_days

        deficit_by_key = defaultdict(float)
        for employee, rule, deficit_hours, source, log_source in deficit_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            dt = source[source._time_rule_span_start_field]
            hours_per_day = hpd_cache[employee.id, dt.date() if hasattr(dt, 'date') else dt]
            deduct = deficit_hours * rule.leave_compensation_rate / hours_per_day
            if deduct > 0:
                deficit_by_key[employee, rule.allocation_type_id] += deduct
                log_by_source[log_source._name, log_source.id, employee, rule.allocation_type_id] -= deduct

        all_keys = set(excess_by_key) | set(deficit_by_key)
        if not all_keys:
            return
        employees = self.env['hr.employee'].browse({e.id for e, _ in all_keys})
        types = self.env['hr.work.entry.type'].browse({t.id for _, t in all_keys})
        alloc_cache = employees._fetch_valid_allocations(types, min(emps_by_date))

        alloc_by_key = {}
        alloc_create_vals = []
        alloc_create_keys = []
        for (employee, alloc_type), alloc_days in excess_by_key.items():
            open_ended = [a for a in alloc_cache.get((employee, alloc_type), []) if not a.date_to]
            if open_ended:
                open_ended[0].number_of_days += alloc_days
                alloc_by_key[employee, alloc_type] = open_ended[0]
            else:
                alloc_create_vals.append({
                    'employee_id': employee.id,
                    'work_entry_type_id': alloc_type.id,
                    'number_of_days': alloc_days,
                    'date_to': False,
                    'state': 'confirm',
                })
                alloc_create_keys.append((employee, alloc_type))
        if alloc_create_vals:
            new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True).create(alloc_create_vals)
            new_allocs.with_context(**approve_ctx).action_approve()
            for key, alloc in zip(alloc_create_keys, new_allocs):
                alloc_by_key[key] = alloc

        deficit_create_vals = []
        deficit_create_keys = []
        for (employee, alloc_type), deduct in deficit_by_key.items():
            allocations = alloc_cache.get((employee, alloc_type), self.env['hr.leave.allocation'])
            remaining = deduct
            for allocation in allocations:
                if remaining <= 0:
                    break
                take = min(remaining, max(0.0, allocation.number_of_days))
                if take > 0:
                    allocation.number_of_days -= take
                    alloc_by_key.setdefault((employee, alloc_type), allocation)
                    remaining -= take
            if remaining > 0 and alloc_type.allows_negative:
                if allocations:
                    allocations[-1].number_of_days -= remaining
                    alloc_by_key.setdefault((employee, alloc_type), allocations[-1])
                else:
                    deficit_create_vals.append({
                        'employee_id': employee.id,
                        'work_entry_type_id': alloc_type.id,
                        'number_of_days': -remaining,
                        'date_to': False,
                        'state': 'confirm',
                    })
                    deficit_create_keys.append((employee, alloc_type))
        if deficit_create_vals:
            new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True).create(deficit_create_vals)
            new_allocs.with_context(**approve_ctx).action_approve()
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

    def _filter_deficit_exceeding_allocation(self, deficit):
        """Drop the deficits the allocation of the rule cannot cover.

        When the total deduction of an employee and allocation type exceeds the balance, all
        the deficit intervals of that pair are dropped, so no output is created for them.

        :param dict deficit: ``{employee: {source: [(start, stop, rule)]}}``
        :return: the filtered ``deficit``
        :rtype: dict
        """
        # pre-fetch version-aware hours_per_day for all (employee, date) pairs
        emps_by_date = defaultdict(lambda: self.env['hr.employee'])
        for employee, by_source in deficit.items():
            for _source, intervals in by_source.items():
                for iv_start, iv_end, rule in intervals:
                    if iv_end > iv_start and rule.leave_compensation_rate > 0 and rule.allocation_type_id:
                        emps_by_date[iv_start.date()] |= employee
        hpd_cache = {}
        for iv_date, employees in emps_by_date.items():
            for emp_id, hpd in employees._get_hours_per_day_batch(iv_date).items():
                hpd_cache[emp_id, iv_date] = hpd or 8.0

        # first pass: total deduction per (employee, alloc_type)
        total_deduct = defaultdict(float)
        for employee, by_source in deficit.items():
            for source, intervals in by_source.items():
                by_period = defaultdict(list)
                for iv_start, iv_end, rule in intervals:
                    if iv_end <= iv_start:
                        continue
                    if rule.quantity_period == 'week':
                        ws = int(rule.week_start or '0')
                        days_to_end = ((ws - 1) % 7 - iv_start.weekday()) % 7
                        period_key = iv_start.date() + timedelta(days=days_to_end)
                    else:
                        period_key = iv_start.date()
                    by_period[period_key].append((iv_start, iv_end, rule))
                for _period_key, period_ivs in by_period.items():
                    winning_rule = min(period_ivs, key=lambda t: t[2].sequence)[2]
                    for iv_start, iv_end, rule in period_ivs:
                        if rule != winning_rule:
                            continue
                        if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                            continue
                        deficit_hours = (iv_end - iv_start).total_seconds() / 3600
                        hours_per_day = hpd_cache[employee.id, iv_start.date()]
                        deduct = deficit_hours * rule.leave_compensation_rate / hours_per_day
                        if deduct > 0:
                            total_deduct[employee, rule.allocation_type_id] += deduct

        if not total_deduct:
            return deficit

        # second pass: check which keys lack sufficient balance
        employees = self.env['hr.employee'].browse({e.id for e, _ in total_deduct})
        types = self.env['hr.work.entry.type'].browse({t.id for _, t in total_deduct})
        alloc_cache = employees._fetch_valid_allocations(types, min(emps_by_date))
        skip_keys = set()
        for (employee, alloc_type), deduct in total_deduct.items():
            allocations = alloc_cache.get((employee, alloc_type), self.env['hr.leave.allocation'])
            positive_total = sum(a.number_of_days for a in allocations if a.number_of_days > 0)
            available = positive_total
            if alloc_type.allows_negative:
                existing_negative = sum(abs(a.number_of_days) for a in allocations if a.number_of_days < 0)
                available += max(0, alloc_type.max_allowed_negative - existing_negative)
            if deduct > available:
                skip_keys.add((employee, alloc_type))

        if not skip_keys:
            return deficit

        # third pass: rebuild deficit without intervals tied to over-drawn keys
        filtered = {}
        for employee, by_source in deficit.items():
            filtered_by_source = {}
            for source, intervals in by_source.items():
                kept = [
                    (iv_start, iv_end, rule)
                    for iv_start, iv_end, rule in intervals
                    if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id)
                    or (employee, rule.allocation_type_id) not in skip_keys
                ]
                if kept:
                    filtered_by_source[source] = kept
            if filtered_by_source:
                filtered[employee] = filtered_by_source
        return filtered

    def _apply_leave_output(self, excess, deficit, active_iv=None):
        """Apply the time rule result on time off sources.

        Creates the outputs (``_apply_output``, defined by ``hr_work_entry``), credits the
        allocations (:meth:`_apply_allocation_credits`) and recreates the resource leaves of the
        sources and outputs.

        :param dict excess: ``{employee: {source: [_Iv]}}``
        :param dict deficit: ``{employee: {source: [(start, stop, rule)]}}``
        :param dict active_iv: ``{employee: {source: Intervals}}``
        """
        deficit = self._filter_deficit_exceeding_allocation(deficit)
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
        :raise ValidationError: when the reversal would bring a balance below its minimum
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
        trigger_desc = self.env.context.get('time_rule_trigger_desc', '')
        errors = []
        for allocation, days in by_alloc.items():
            if not allocation.exists() or not days:
                continue
            wet = allocation.work_entry_type_id
            allowed_floor = -wet.max_allowed_negative if wet.allows_negative else 0.0
            # the balance is in the unit of the type, the credits in days
            hours_per_day = (allocation._get_employee_hours_per_day() or 8.0) if wet.unit_of_measure == 'hour' else 1.0
            remaining_after = allocation.virtual_remaining_leaves / hours_per_day - days
            allowed_floor /= hours_per_day
            if remaining_after < allowed_floor:
                employee = allocation.employee_id
                manager = employee.leave_manager_id or employee.parent_id
                manager_name = manager.name if manager else self.env._('your HR manager')
                if trigger_desc:
                    errors.append(self.env._(
                        "Saving %(record)s requires reducing %(employee)s's '%(leave_type)s' balance "
                        "by %(days).4g day(s), but %(taken).4g day(s) have already been taken against it. "
                        "Please ask %(manager)s to refuse or reduce those taken leaves first, "
                        "or adjust the allocation manually.",
                        record=trigger_desc,
                        employee=employee.name,
                        leave_type=wet.name,
                        days=days,
                        taken=days - (remaining_after - allowed_floor),
                        manager=manager_name,
                    ))
                else:
                    errors.append(self.env._(
                        "Cannot reduce %(employee)s's '%(leave_type)s' balance by %(days).4g day(s): "
                        "%(taken).4g day(s) have already been taken against it (balance would drop to "
                        "%(after).4g, below the minimum of %(floor).4g). "
                        "Please ask %(manager)s to refuse or reduce those taken leaves first, "
                        "or adjust the allocation manually.",
                        employee=employee.name,
                        leave_type=wet.name,
                        days=days,
                        taken=days - (remaining_after - allowed_floor),
                        after=remaining_after,
                        floor=allowed_floor,
                        manager=manager_name,
                    ))
        if errors:
            raise ValidationError('\n'.join(errors))
        for allocation, days in by_alloc.items():
            if not allocation.exists() or not days:
                continue
            allocation.number_of_days -= days
        logs.unlink()
