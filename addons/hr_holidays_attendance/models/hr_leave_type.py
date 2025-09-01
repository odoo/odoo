# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import format_duration
from odoo import _, api, fields, models


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

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

    def get_allocation_data(self, employees, date=None):
        res = super().get_allocation_data(employees, date)
        deductible_time_off_types = self.env['hr.leave.type'].search([
            ('overtime_deductible', '=', True),
            ('requires_allocation', '=', 'no')])
        for employee in employees:
            for leave_type in deductible_time_off_types:
                if leave_type in self and employee.sudo().total_overtime > 0:
                    lt_info = (
                        leave_type.name,
                        {
                            'remaining_leaves': 0,
                            'virtual_remaining_leaves': employee.sudo().total_overtime,
                            'max_leaves': 0,
                            'leaves_taken': 0,
                            'virtual_leaves_taken': 0,
                            'closest_allocation_remaining': 0,
                            'closest_allocation_expire': False,
                            'total_virtual_excess': 0,
                            'virtual_excess_data': {},
                            'request_unit': leave_type.request_unit,
                            'icon': leave_type.sudo().icon_id.url,
                            'allows_negative': leave_type.allows_negative,
                            'max_allowed_negative': leave_type.max_allowed_negative,
                            'overtime_deductible': True
                        },
                        leave_type.requires_allocation,
                        leave_type.id)
                    res[employee].append(lt_info)
        return res
