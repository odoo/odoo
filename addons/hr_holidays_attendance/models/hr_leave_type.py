# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    hr_attendance_overtime = fields.Boolean(related='company_id.hr_attendance_overtime')
    overtime_deductible = fields.Boolean("Deduct Extra Hours", default=False,
                                         help="""Once a time off of this type is approved, extra hours in attendances
                                         will be deducted.""")

    def get_employees_days(self, employee_ids):
        res = super().get_employees_days(employee_ids)
        deductibles = self.env['hr.leave.type'].search([('overtime_deductible', '=', True), ('allocation_type', '=', 'no')]).ids
        for employee_id, allocations in res.items():
            for allocation_id in allocations:
                if allocation_id in deductibles:
                    # todo opt-y-mize
                    res[employee_id][allocation_id]['virtual_remaining_leaves'] = self.env['hr.employee'].sudo().browse(employee_id).total_overtime
                    res[employee_id][allocation_id]['overtime_deductible'] = True
                else:
                    res[employee_id][allocation_id]['overtime_deductible'] = False
        return res

    def _format_leave_request(self):
        return super()._format_leave_request() + (self.overtime_deductible, )
