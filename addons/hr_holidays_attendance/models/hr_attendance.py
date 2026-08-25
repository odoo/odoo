# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import AND
from odoo.addons.resource.models.utils import sum_intervals


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def _get_overtime_leave_domain(self):
        domain = super()._get_overtime_leave_domain()
        # resource_id = False => Public holidays
        return AND([domain, ['|', ('holiday_id.holiday_status_id.time_type', '=', 'leave'), ('resource_id', '=', False)]])

    def _gantt_compute_max_work_hours_within_interval(self, employee, start, stop):
        """ Override of `hr_attendance_gantt`. For flexible employees, virtual attendances are centered
        at noon so hour-based time offs outside that window are not subtracted automatically. """
        res = super()._gantt_compute_max_work_hours_within_interval(employee, start, stop)
        employee_sudo = employee.sudo()
        if not employee_sudo.is_flexible or employee_sudo.is_fully_flexible:
            return res
        # For flexible employees, virtual attendances are centered at noon so hour-based time offs outside
        # that window are not subtracted automatically.
        attendance_intervals = employee_sudo.resource_calendar_id._work_intervals_batch(start, stop, employee_sudo.resource_id, compute_leaves=False)[employee_sudo.resource_id.id]
        leaves_intervals = employee_sudo.resource_calendar_id._leave_intervals_batch(start, stop, employee_sudo.resource_id, [('holiday_id.request_unit_hours', '=', True)])[employee_sudo.resource_id.id]
        uncovered = leaves_intervals - attendance_intervals
        return max(0.0, res - sum_intervals(uncovered))
