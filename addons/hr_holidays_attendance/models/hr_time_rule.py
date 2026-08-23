# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    def _apply_attendance_output(self, excess, deficit, active_iv=None):
        _new_records, _all_source_ids, excess_alloc, deficit_alloc = self._apply_output(excess, deficit, active_iv=active_iv)

        # accumulate days per (employee, allocation_type) before any DB writes so that
        # multiple rules targeting the same allocation type in one transaction produce a
        # single allocation record rather than one per rule.
        excess_by_key = defaultdict(float)
        for employee, rule, excess_hours in excess_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            alloc_days = excess_hours * rule.leave_compensation_rate / hours_per_day
            if alloc_days > 0:
                excess_by_key[(employee, rule.allocation_type_id)] += alloc_days

        alloc_create_vals = []
        for (employee, alloc_type), alloc_days in excess_by_key.items():
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', alloc_type.id),
                ('state', '=', 'validate'),
                ('date_to', '=', False),
            ], limit=1)
            if allocation:
                allocation.number_of_days += alloc_days
            else:
                alloc_create_vals.append({
                    'employee_id': employee.id,
                    'work_entry_type_id': alloc_type.id,
                    'number_of_days': alloc_days,
                    'date_to': False,
                    'state': 'confirm',
                })
        if alloc_create_vals:
            new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True).create(alloc_create_vals)
            new_allocs.action_approve()

        deficit_by_key = defaultdict(float)
        for employee, rule, deficit_hours in deficit_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            deduct = deficit_hours * rule.leave_compensation_rate / hours_per_day
            if deduct > 0:
                deficit_by_key[(employee, rule.allocation_type_id)] += deduct

        for (employee, alloc_type), deduct in deficit_by_key.items():
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', alloc_type.id),
                ('state', '=', 'validate'),
                ('date_to', '=', False),
            ], limit=1)
            if allocation:
                allocation.number_of_days = max(0, allocation.number_of_days - deduct)
