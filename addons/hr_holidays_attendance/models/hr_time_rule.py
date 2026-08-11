# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    def _apply_attendance_output(self, excess, deficit, active_iv=None):
        _new_records, _all_source_ids, excess_alloc, deficit_alloc = self._apply_output(excess, deficit, active_iv=active_iv)
        alloc_create_vals = []
        for employee, rule, excess_hours in excess_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            alloc_days = excess_hours * rule.leave_compensation_rate / hours_per_day
            if alloc_days <= 0:
                continue
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', rule.allocation_type_id.id),
                ('state', '=', 'validate'),
                ('date_to', '=', False),
            ], limit=1)
            if allocation:
                allocation.number_of_days += alloc_days
            else:
                alloc_create_vals.append({
                    'employee_id': employee.id,
                    'work_entry_type_id': rule.allocation_type_id.id,
                    'number_of_days': alloc_days,
                    'date_to': False,
                    'state': 'confirm',
                })
        if alloc_create_vals:
            new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True).create(alloc_create_vals)
            new_allocs.action_approve()
        for employee, rule, deficit_hours in deficit_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            deduct = deficit_hours * rule.leave_compensation_rate / hours_per_day
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', rule.allocation_type_id.id),
                ('state', '=', 'validate'),
                ('date_to', '=', False),
            ], limit=1)
            if allocation:
                allocation.number_of_days = max(0, allocation.number_of_days - deduct)
