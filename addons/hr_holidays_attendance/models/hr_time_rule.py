# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    def _apply_attendance_output(self, excess, deficit, active_iv=None):
        _new_records, _all_source_ids, excess_alloc, deficit_alloc = super()._apply_attendance_output(excess, deficit, active_iv=active_iv)

        # accumulate days per (employee, allocation_type) before any DB writes so that
        # multiple rules targeting the same allocation type in one transaction produce a
        # single allocation record rather than one per rule.
        excess_by_key = defaultdict(float)
        # per-source credit log: (source_model, source_id, employee, alloc_type) -> days
        log_by_source = defaultdict(float)

        for employee, rule, excess_hours, source, log_source in excess_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            alloc_days = excess_hours * rule.leave_compensation_rate / hours_per_day
            if alloc_days > 0:
                excess_by_key[employee, rule.allocation_type_id] += alloc_days
                log_by_source[log_source._name, log_source.id, employee, rule.allocation_type_id] += alloc_days

        # track resolved allocations so we can write log entries afterwards
        alloc_by_key = {}
        alloc_create_vals = []
        alloc_create_keys = []
        for (employee, alloc_type), alloc_days in excess_by_key.items():
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', alloc_type.id),
                ('state', '=', 'validate'),
                ('date_to', '=', False),
            ], limit=1)
            if allocation:
                allocation.number_of_days += alloc_days
                alloc_by_key[employee, alloc_type] = allocation
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
            new_allocs.action_approve()
            for key, alloc in zip(alloc_create_keys, new_allocs):
                alloc_by_key[key] = alloc

        deficit_by_key = defaultdict(float)
        for employee, rule, deficit_hours, source, log_source in deficit_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            deduct = deficit_hours * rule.leave_compensation_rate / hours_per_day
            if deduct > 0:
                deficit_by_key[employee, rule.allocation_type_id] += deduct
                log_by_source[log_source._name, log_source.id, employee, rule.allocation_type_id] -= deduct

        for (employee, alloc_type), deduct in deficit_by_key.items():
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', alloc_type.id),
                ('state', '=', 'validate'),
                ('date_to', '=', False),
            ], limit=1)
            if allocation:
                allocation.number_of_days = max(0, allocation.number_of_days - deduct)
                alloc_by_key.setdefault((employee, alloc_type), allocation)

        # write credit log: one row per (source, allocation) so reversal is exact
        log_vals = []
        for (source_model, source_id, employee, alloc_type), days in log_by_source.items():
            allocation = alloc_by_key.get((employee, alloc_type))
            if allocation and days:
                log_vals.append({
                    'source_model': source_model,
                    'source_id': source_id,
                    'allocation_id': allocation.id,
                    'days': days,
                })
        if log_vals:
            self.env['hr.time.rule.allocation.log'].sudo().create(log_vals)
