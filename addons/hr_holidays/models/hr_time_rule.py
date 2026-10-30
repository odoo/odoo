# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.hr_work_entry.models.hr_time_rule import utc_to_local


class HrTimeRuleSourceMixin(models.AbstractModel):
    _inherit = 'hr.time.rule.source.mixin'

    def _on_sources_collected(self, sources):
        """Reverse the allocation credits of the sources before they are evaluated again.

        :param sources: records of the source model
        """
        self.env['hr.time.rule']._reverse_allocation_credits(self._name, sources.ids)


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
        merged_intervals = []
        merge_key_of_last_merged_interval = None
        for interval in super()._resolve_output_intervals(intervals):
            merge_key = interval.classifying_rule._get_output_leave_merge_key(premium_pay_category_ids=interval.premium_pay_category_ids)
            last_merged_interval = merged_intervals[-1] if merged_intervals else None
            if (
                last_merged_interval
                and last_merged_interval.end == interval.start
                and merge_key_of_last_merged_interval == merge_key
            ):
                merged_intervals[-1] = last_merged_interval._replace(
                    end=interval.end,
                    premium_pay_category_ids=last_merged_interval.premium_pay_category_ids | interval.premium_pay_category_ids,
                )
            else:
                merged_intervals.append(interval)
                merge_key_of_last_merged_interval = merge_key
        return merged_intervals

    def _get_output_leave_vals(self, employee, rule, date_from, date_to, source_leave, premium_pay_category_ids=frozenset()):
        """Return the creation values of a validated time off output by ``rule``.

        The output has the rule's type, ``time_rule_id``, the given span and is linked to
        ``source_leave``.

        :param employee: ``hr.employee``
        :param rule: ``hr.time.rule`` producing the output
        :param datetime date_from: start, naive UTC
        :param datetime date_to: end, naive UTC
        :param source_leave: source ``hr.leave``
        :param frozenset premium_pay_category_ids: premium pay ids
        :rtype: dict
        """
        timezone = ZoneInfo(employee._get_tz())
        local_date_from = utc_to_local(date_from, timezone)
        local_date_to = utc_to_local(date_to, timezone)
        return {
            'employee_id': employee.id,
            'work_entry_type_id': rule.work_entry_type_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': local_date_from.date(),
            'request_date_to': local_date_to.date(),
            'request_hour_from': local_date_from.hour + local_date_from.minute / 60,
            'request_hour_to': local_date_to.hour + local_date_to.minute / 60,
            'time_rule_id': rule.id,
            'source_leave_id': source_leave.id,
            'resource_calendar_id': source_leave.resource_calendar_id.id,
            'state': 'validate',
        }

    def _get_output_leave_merge_key(self, premium_pay_category_ids=frozenset()):
        """Return the hashable key deciding when consecutive excess slices make one time off.

        Override to add discriminators (e.g. the premium pays in Belgium). Default: the rule.
        """
        return self

    # ------------------------------------------------------------
    # Allocation credits
    # ------------------------------------------------------------

    def _convert_hours_to_allocation_days(self, employee, hours):
        """Return the days to credit (or debit) on the rule's allocation type for `hours` of
        excess (or deficit), or 0 if the rule does not compensate with leaves."""
        self.ensure_one()
        if not (self.leave_compensation_rate > 0 and self.allocation_type_id):
            return 0.0
        hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
        return hours * self.leave_compensation_rate / hours_per_day

    def _find_time_rule_allocations(self, allocation_type, employees):
        """Return the allocation of `allocation_type` credited by time rules, for each of `employees`.

        Time-rule allocations are always open-ended (date_to=False) so they don't
        collide with accrual or fixed-period allocations. If several match, the last created wins.

        :param employees: ``hr.employee`` recordset
        :return: {employee: hr.leave.allocation}, only for the employees having one
        """
        allocations = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', 'in', employees.ids),
            ('work_entry_type_id', '=', allocation_type.id),
            ('state', '=', 'validate'),
            ('date_to', '=', False),
        ], order='create_date desc, id desc')
        # grouped() keeps the search order: the first allocation of each employee is the last created
        return {
            employee: employee_allocations[:1]
            for employee, employee_allocations in allocations.grouped('employee_id').items()
        }

    def _apply_allocation_credits(self, excess_allocation_credits, deficit_allocation_credits):
        """Credit (or deduct) the excess (or missing) hours of rules to allocations, and log it.

        For rules with ``leave_compensation_rate`` and ``allocation_type_id``, the hours times
        the rate, divided by the employee's hours per day, are added to (or deducted from) the
        validated allocation without end date of that type, created if needed. Each credit is
        logged in ``hr.time.rule.allocation.log`` so it can be reversed.

        :param list excess_allocation_credits: ``[employee, rule, hours, source, log_source]`` rows
        :param list deficit_allocation_credits: same rows for the deficits
        """
        days_to_add_by_type = defaultdict(lambda: defaultdict(float))     # allocation type -> employee -> days
        days_to_remove_by_type = defaultdict(lambda: defaultdict(float))  # allocation type -> employee -> days
        logged_days_by_key = defaultdict(float)  # (log model, log id, employee, allocation type) -> days

        for employee, rule, excess_hours, _source_record, log_record in excess_allocation_credits:
            days_to_add = rule._convert_hours_to_allocation_days(employee, excess_hours)
            if days_to_add > 0:
                days_to_add_by_type[rule.allocation_type_id][employee] += days_to_add
                logged_days_by_key[log_record._name, log_record.id, employee, rule.allocation_type_id] += days_to_add

        allocation_by_key = {}  # (employee, allocation type) -> allocation credited or deducted
        allocation_vals_list = []
        keys_of_allocations_to_create = []
        for allocation_type, days_to_add_by_employee in days_to_add_by_type.items():
            employees = self.env['hr.employee'].browse([employee.id for employee in days_to_add_by_employee])
            existing_allocation_by_employee = self._find_time_rule_allocations(allocation_type, employees)
            for employee, days_to_add in days_to_add_by_employee.items():
                allocation = existing_allocation_by_employee.get(employee)
                if allocation:
                    allocation.number_of_days += days_to_add
                    allocation_by_key[employee, allocation_type] = allocation
                    continue
                allocation_vals_list.append({
                    'employee_id': employee.id,
                    'work_entry_type_id': allocation_type.id,
                    'number_of_days': days_to_add,
                    'date_to': False,
                    'state': 'confirm',
                })
                keys_of_allocations_to_create.append((employee, allocation_type))
        if allocation_vals_list:
            created_allocations = self.env['hr.leave.allocation'].sudo().create(allocation_vals_list)
            allocation_by_key.update(zip(keys_of_allocations_to_create, created_allocations))

        for employee, rule, deficit_hours, _source_record, log_record in deficit_allocation_credits:
            days_to_remove = rule._convert_hours_to_allocation_days(employee, deficit_hours)
            if days_to_remove > 0:
                days_to_remove_by_type[rule.allocation_type_id][employee] += days_to_remove
                logged_days_by_key[log_record._name, log_record.id, employee, rule.allocation_type_id] -= days_to_remove

        # searched after the creation above, as a new allocation may already be validated
        for allocation_type, days_to_remove_by_employee in days_to_remove_by_type.items():
            employees = self.env['hr.employee'].browse([employee.id for employee in days_to_remove_by_employee])
            allocation_to_deduct_by_employee = self._find_time_rule_allocations(allocation_type, employees)
            for employee, days_to_remove in days_to_remove_by_employee.items():
                allocation = allocation_to_deduct_by_employee.get(employee)
                if allocation:
                    allocation.number_of_days = max(0, allocation.number_of_days - days_to_remove)
                    allocation_by_key.setdefault((employee, allocation_type), allocation)

        log_vals_list = []
        for (log_model, log_id, employee, allocation_type), days in logged_days_by_key.items():
            allocation = allocation_by_key.get((employee, allocation_type))
            if allocation and days:
                log_vals_list.append({
                    'res_model': log_model,
                    'res_id': log_id,
                    'allocation_id': allocation.id,
                    'days': days,
                })
        if log_vals_list:
            self.env['hr.time.rule.allocation.log'].sudo().create(log_vals_list)

    def _filter_deficit_exceeding_allocation(self, deficit):
        """Drop the deficits the allocation of the rule cannot cover.

        When the total deduction of an employee and allocation type exceeds the balance, all
        the deficit intervals of that pair are dropped, so no output is created for them.

        :param dict deficit: ``{employee: {source: [(start, stop, rule)]}}``
        :return: the filtered ``deficit``
        :rtype: dict
        """
        days_to_remove_by_type = defaultdict(lambda: defaultdict(float))  # allocation type -> employee -> days
        for employee, deficit_by_source in deficit.items():
            for deficit_intervals in deficit_by_source.values():
                for winning_intervals in self._group_deficit_intervals_by_period(deficit_intervals).values():
                    for deficit_start, deficit_stop, rule in winning_intervals:
                        deficit_hours = (deficit_stop - deficit_start).total_seconds() / 3600
                        days_to_remove = rule._convert_hours_to_allocation_days(employee, deficit_hours)
                        if days_to_remove > 0:
                            days_to_remove_by_type[rule.allocation_type_id][employee] += days_to_remove

        overdrawn_keys = set()
        for allocation_type, days_to_remove_by_employee in days_to_remove_by_type.items():
            employees = self.env['hr.employee'].browse([employee.id for employee in days_to_remove_by_employee])
            allocation_by_employee = self._find_time_rule_allocations(allocation_type, employees)
            for employee, days_to_remove in days_to_remove_by_employee.items():
                allocation = allocation_by_employee.get(employee)
                available_days = allocation.number_of_days if allocation else 0.0
                if days_to_remove > available_days:
                    overdrawn_keys.add((employee, allocation_type))
        if not overdrawn_keys:
            return deficit

        def is_overdrawing(employee, rule):
            uses_allocation = rule.leave_compensation_rate > 0 and rule.allocation_type_id
            return uses_allocation and (employee, rule.allocation_type_id) in overdrawn_keys

        filtered_deficit = {}
        for employee, deficit_by_source in deficit.items():
            filtered_deficit_by_source = {}
            for source_record, deficit_intervals in deficit_by_source.items():
                kept_intervals = [
                    (deficit_start, deficit_stop, rule)
                    for deficit_start, deficit_stop, rule in deficit_intervals
                    if not is_overdrawing(employee, rule)
                ]
                if kept_intervals:
                    filtered_deficit_by_source[source_record] = kept_intervals
            if filtered_deficit_by_source:
                filtered_deficit[employee] = filtered_deficit_by_source
        return filtered_deficit

    def _apply_leave_output(self, excess, deficit, source_intervals_by_employee=None):
        """Apply the time rule result on time off sources.

        Creates the outputs (``_apply_output``, defined by ``hr_work_entry``), credits the
        allocations (:meth:`_apply_allocation_credits`) and recreates the resource leaves of the
        sources and outputs.

        :param dict excess: ``{employee: {source: [PipelineInterval]}}``
        :param dict deficit: ``{employee: {source: [(start, stop, rule)]}}``
        :param dict source_intervals_by_employee: ``{employee: {source: Intervals}}``
        """
        deficit = self._filter_deficit_exceeding_allocation(deficit)
        created_leaves, processed_source_ids, excess_allocation_credits, deficit_allocation_credits = self._apply_output(excess, deficit, source_intervals_by_employee=source_intervals_by_employee)
        self._apply_allocation_credits(excess_allocation_credits, deficit_allocation_credits)
        if not processed_source_ids:
            return
        Leave = self.env['hr.leave'].sudo()
        source_leaves = Leave.with_context(active_test=False).browse(list(processed_source_ids))
        (source_leaves | created_leaves).with_context(**Leave._time_rule_write_ctx)._create_resource_leave()

    def _get_allocation_reversal_error_message(self, allocation, days, remaining_days_after, allowed_floor, trigger_desc):
        employee = allocation.employee_id
        leave_type = allocation.work_entry_type_id
        manager = employee.leave_manager_id or employee.parent_id
        manager_name = manager.name if manager else self.env._('your HR manager')
        taken_days = days - (remaining_days_after - allowed_floor)
        if trigger_desc:
            return self.env._(
                "Saving %(record)s requires reducing %(employee)s's '%(leave_type)s' balance "
                "by %(days).4g day(s), but %(taken).4g day(s) have already been taken against it. "
                "Please ask %(manager)s to refuse or reduce those taken leaves first, "
                "or adjust the allocation manually.",
                record=trigger_desc,
                employee=employee.name,
                leave_type=leave_type.name,
                days=days,
                taken=taken_days,
                manager=manager_name,
            )
        return self.env._(
            "Cannot reduce %(employee)s's '%(leave_type)s' balance by %(days).4g day(s): "
            "%(taken).4g day(s) have already been taken against it (balance would drop to "
            "%(after).4g, below the minimum of %(floor).4g). "
            "Please ask %(manager)s to refuse or reduce those taken leaves first, "
            "or adjust the allocation manually.",
            employee=employee.name,
            leave_type=leave_type.name,
            days=days,
            taken=taken_days,
            after=remaining_days_after,
            floor=allowed_floor,
            manager=manager_name,
        )

    @api.model
    def _reverse_allocation_credits(self, source_model, source_ids):
        """Reverse the allocation credits logged for the given source records.

        :param str source_model: ``'hr.leave'`` or ``'hr.attendance'``
        :param source_ids: ids of the sources
        :raise ValidationError: when the reversal would bring a balance below its minimum
        """
        if not source_ids:
            return
        logs = self.env['hr.time.rule.allocation.log'].sudo().search([
            ('res_model', '=', source_model),
            ('res_id', 'in', list(source_ids)),
        ])
        if not logs:
            return
        logged_days_by_allocation = defaultdict(float)
        for log in logs:
            logged_days_by_allocation[log.allocation_id] += log.days
        days_to_reverse_by_allocation = {
            allocation: days
            for allocation, days in logged_days_by_allocation.items()
            if days and allocation.exists()
        }

        trigger_desc = self.env.context.get('time_rule_trigger_desc', '')
        error_messages = []
        for allocation, days in days_to_reverse_by_allocation.items():
            leave_type = allocation.work_entry_type_id
            allowed_floor = -leave_type.max_allowed_negative if leave_type.allows_negative else 0.0
            # the balance is in the unit of the type, the credits in days
            hours_per_day = (allocation._get_employee_hours_per_day() or 8.0) if leave_type.unit_of_measure == 'hour' else 1.0
            remaining_days_after = allocation.virtual_remaining_leaves / hours_per_day - days
            allowed_floor /= hours_per_day
            if remaining_days_after < allowed_floor:
                error_messages.append(self._get_allocation_reversal_error_message(
                    allocation, days, remaining_days_after, allowed_floor, trigger_desc,
                ))
        if error_messages:
            raise ValidationError('\n'.join(error_messages))

        for allocation, days in days_to_reverse_by_allocation.items():
            allocation.number_of_days -= days
        logs.unlink()
