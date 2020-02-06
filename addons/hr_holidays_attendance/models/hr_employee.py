# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.resource.models.resource import HOURS_PER_DAY


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    def _compute_extra_hours(self):
        super()._compute_extra_hours()
        for employee in self:
            if employee.attendance_ids:
                read_group_results = self.env['hr.leave.allocation'].read_group(
                    domain=[('employee_id', '=', employee.id),
                            ('holiday_status_id.deduct_from_extra_hours', '=', True),
                            ('state', '=', 'validate')],
                    fields=['number_of_days'],
                    groupby=['employee_id']
                )
                # If there are deductable leave allocations that have been approved, then they will be deducted
                # from the total of extra hours
                if read_group_results:
                    approved_deducted_days = read_group_results[0]
                    approved_deducted_hours = approved_deducted_days['number_of_days'] * (employee.resource_calendar_id.hours_per_day or HOURS_PER_DAY)
                    employee.extra_hours -= approved_deducted_hours
