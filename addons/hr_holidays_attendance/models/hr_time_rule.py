# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    def _apply_attendance_output(self, excess, deficit):
        super()._apply_attendance_output(excess, deficit)
        self._apply_allocation_compensation(excess, deficit)

    def _apply_allocation_compensation(self, excess, deficit):
        """Manage hr.leave.allocation balances for time rule outputs."""
        alloc_create_vals = []

        for employee, by_source in excess.items():
            for _source_att, intervals in by_source.items():
                for s, e, rule in self._resolve_output_intervals(intervals):
                    if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                        continue
                    alloc_days = (e - s).total_seconds() / 3600 * rule.leave_compensation_rate / 100
                    allocation = self.env['hr.leave.allocation'].sudo().search([
                        ('employee_id', '=', employee.id),
                        ('work_entry_type_id', '=', rule.allocation_type_id.id),
                        ('state', '=', 'validate'),
                    ], limit=1)
                    if allocation:
                        allocation.number_of_days += alloc_days
                    else:
                        alloc_create_vals.append({
                            'employee_id': employee.id,
                            'work_entry_type_id': rule.allocation_type_id.id,
                            'number_of_days': alloc_days,
                            'state': 'confirm',
                        })

        if alloc_create_vals:
            new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True).create(alloc_create_vals)
            new_allocs.action_approve()

        for employee, by_source in deficit.items():
            for _source_att, intervals in by_source.items():
                effective_rule = min(
                    (rule for _, _, rule in intervals if rule.work_entry_type_id),
                    key=lambda r: r.sequence,
                    default=None,
                )
                if not effective_rule:
                    continue
                for s, e, rule in intervals:
                    if rule != effective_rule or e <= s:
                        continue
                    if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                        continue
                    deduct = (e - s).total_seconds() / 3600 * rule.leave_compensation_rate / 100
                    allocation = self.env['hr.leave.allocation'].sudo().search([
                        ('employee_id', '=', employee.id),
                        ('work_entry_type_id', '=', rule.allocation_type_id.id),
                        ('state', '=', 'validate'),
                    ], limit=1)
                    if allocation:
                        allocation.number_of_days -= deduct
