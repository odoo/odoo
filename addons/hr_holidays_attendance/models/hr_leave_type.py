# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import format_duration
from odoo import _, api, fields, models


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    hr_attendance_overtime = fields.Boolean(compute='_compute_hr_attendance_overtime')
    overtime_deductible = fields.Boolean(
        "Deduct Extra Hours", default=False,
        help="Once a time off of this type is approved, extra hours in attendances will be deducted.")

    @api.depends('overtime_deductible', 'requires_allocation')
    @api.depends_context('request_type', 'leave', 'holiday_status_display_name', 'employee_id')
    def _compute_display_name(self):
        # Exclude hours available in allocation contexts, it might be confusing otherwise
        if not self.requested_display_name() or self._context.get('request_type', 'leave') == 'allocation':
            return super()._compute_display_name()

        employee = self.env['hr.employee'].browse(self._context.get('employee_id')).sudo()
        if employee.total_overtime <= 0:
            return super()._compute_display_name()

        overtime_leaves = self.filtered(lambda l_type: l_type.overtime_deductible and l_type.requires_allocation == 'no')
        for leave_type in overtime_leaves:
            leave_type.display_name = "%(name)s (%(count)s)" % {
                'name': leave_type.name,
                'count': _('%s hours available',
                    format_duration(employee.total_overtime)),
            }
        super(HRLeaveType, self - overtime_leaves)._compute_display_name()

    def get_employees_days(self, employee_ids, date=None):
        res = super().get_employees_days(employee_ids, date)
        deductible_time_off_type_ids = self.env['hr.leave.type'].search([
            ('overtime_deductible', '=', True),
            ('requires_allocation', '=', 'no')]).ids
        for employee_id, allocations in res.items():
            for allocation_id in allocations:
                if allocation_id in deductible_time_off_type_ids:
                    res[employee_id][allocation_id]['virtual_remaining_leaves'] = self.env['hr.employee'].sudo().browse(employee_id).total_overtime
                    res[employee_id][allocation_id]['overtime_deductible'] = True
                else:
                    res[employee_id][allocation_id]['overtime_deductible'] = False
        return res

    def _get_days_request(self):
        res = super()._get_days_request()
        res[1]['overtime_deductible'] = self.overtime_deductible
        return res

    @api.depends('company_id.hr_attendance_overtime')
    def _compute_hr_attendance_overtime(self):
        # If no company is linked to the time off type, use the current company's setting
        for leave_type in self:
            if leave_type.company_id:
                leave_type.hr_attendance_overtime = leave_type.company_id.hr_attendance_overtime
            else:
                leave_type.hr_attendance_overtime = self.env.company.hr_attendance_overtime
