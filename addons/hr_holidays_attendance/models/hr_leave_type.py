# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    hr_attendance_overtime = fields.Boolean(compute='_compute_hr_attendance_overtime')
    overtime_deductible = fields.Boolean(
        "Deduct Extra Hours", default=False,
        help="Once a time off of this type is approved, extra hours in attendances will be deducted.")

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
