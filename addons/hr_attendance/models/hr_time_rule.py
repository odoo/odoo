# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    condition_work_entry_type_ids = fields.Many2many(
        default=lambda self: self.env.company.attendance_work_entry_type_id
    )

    def _get_applicable_employees(self, employees):
        result = super()._get_applicable_employees(employees)
        if self.calendar_source == 'employee':
            result = result.filtered('resource_calendar_id')
        return result

    def _get_output_attendance_vals(self, employee, rule, check_in, check_out, source_attendance=None, accumulated_pp=frozenset()):
        return {
            'employee_id': employee.id,
            'work_entry_type_id': rule.work_entry_type_id.id,
            'check_in': check_in,
            'check_out': check_out,
            'source_attendance_id': source_attendance.id if source_attendance else False,
            'time_rule_id': rule.id,
        }

    def _apply_attendance_output(self, excess, deficit):
        self._apply_output(excess, deficit)
