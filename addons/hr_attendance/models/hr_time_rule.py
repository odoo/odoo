# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    condition_work_entry_type_ids = fields.Many2many(
        default=lambda self: self.env.company.attendance_work_entry_type_id
    )

    def _get_applicable_employees(self, employees):
        """Also drop the employees without schedule for the rules based on the employee
        schedule (``calendar_source = 'employee'``)."""
        result = super()._get_applicable_employees(employees)
        if self.calendar_source == 'employee':
            result = result.filtered('resource_calendar_id')
        return result

    def _get_output_attendance_vals(self, employee, check_in, check_out, source_attendance=None, premium_pay_category_ids=frozenset()):
        """Return the creation values of an output attendance of the rule.

        :param employee: ``hr.employee``
        :param datetime check_in: naive UTC
        :param datetime check_out: naive UTC
        :param source_attendance: the source ``hr.attendance``
        :param frozenset premium_pay_category_ids: premium pay ids, used by overrides (``hr_payroll``)
        :return: ``employee_id``, ``work_entry_type_id`` (the rule's output type),
            ``check_in``, ``check_out``, ``source_attendance_id`` and ``time_rule_id``
        :rtype: dict
        """
        self.ensure_one()
        return {
            'employee_id': employee.id,
            'work_entry_type_id': self.work_entry_type_id.id,
            'check_in': check_in,
            'check_out': check_out,
            'source_attendance_id': source_attendance.id if source_attendance else False,
            'time_rule_id': self.id,
        }

    def _apply_attendance_output(self, excess, deficit, source_intervals_by_employee=None):
        """Write the time rule results on attendances (``hr.time.rule._apply_output``).

        ``hr_holidays_attendance`` extends it to credit or deduct allocations.

        :return: the result of ``_apply_output``: ``(new_records, all_source_ids, excess_allocation_credits,
            deficit_allocation_credits)``
        :rtype: tuple
        """
        return self._apply_output(excess, deficit, source_intervals_by_employee=source_intervals_by_employee)
