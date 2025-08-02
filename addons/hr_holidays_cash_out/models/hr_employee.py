from collections import defaultdict

from odoo import models


class HrEmployee(models.AbstractModel):
    _inherit = "hr.employee"

    def _get_consumed_cash_out(self, leave_types, allocations_per_employee_type, allocations_leaves_consumed, to_recheck_leaves_per_leave_type):
        employees = self or self._get_contextual_employee()
        cash_outs_domain = [
            ('leave_type_id', 'in', leave_types.ids),
            ('employee_id', 'in', employees.ids),
            ('state', 'in', ['confirm', 'validate1', 'validate', 'paid']),
        ]
        if self.env.context.get('ignored_cash_out_ids'):
            cash_outs_domain.append(('id', 'not in', self.env.context.get('ignored_cash_out_ids')))
        cash_outs = self.env['hr.leave.cash.out'].search(cash_outs_domain)
        cash_outs_per_employee_type = defaultdict(lambda: defaultdict(lambda: self.env['hr.leave.cash.out']))
        for cash_out in cash_outs:
            cash_outs_per_employee_type[cash_out.employee_id][cash_out.leave_type_id] |= cash_out
        for employee in employees:
            for leave_type in leave_types:
                leave_allocations = allocations_per_employee_type[employee][leave_type]
                leave_type_data = allocations_leaves_consumed[employee][leave_type]
                for cash_out in cash_outs_per_employee_type[employee][leave_type]:
                    if not leave_type.requires_allocation:
                        continue

                    quantity = cash_out.quantity

                    for allocation in leave_allocations:
                        if allocation.date_from > cash_out.create_date or (allocation.date_to and allocation.date_to < cash_out.create_date):
                            continue
                        max_allowed_duration = min(
                            quantity,
                            leave_type_data[allocation]['virtual_remaining_leaves'],
                        )
                        if not max_allowed_duration:
                            continue
                        allocated_time = min(max_allowed_duration, quantity)
                        leave_type_data[allocation]['virtual_leaves_taken'] += allocated_time
                        leave_type_data[allocation]['virtual_remaining_leaves'] -= allocated_time
                        leave_type_data[allocation]['virtual_cash_out_taken'] += allocated_time
                        if cash_out.state == 'validate':
                            leave_type_data[allocation]['leaves_taken'] += allocated_time
                            leave_type_data[allocation]['remaining_leaves'] -= allocated_time
                            leave_type_data[allocation]['cash_out_taken'] += allocated_time

                        quantity -= allocated_time
                        if not quantity:
                            break
                    # This needs to be investigated again
                    if round(quantity, 2) > 0:
                        to_recheck_leaves_per_leave_type[employee][leave_type]['excess_days']['cash_out'] = {
                            'amount': quantity,
                            'is_virtual': cash_out.state != 'validate',
                            'cash_out_id': cash_out.id,
                        }
