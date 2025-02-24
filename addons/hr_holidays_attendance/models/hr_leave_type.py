# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import format_duration
from odoo import _, api, fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    requires_allocation = fields.Selection(selection_add=[('extra_hours', 'Based on Extra Hours')], ondelete={'extra_hours': 'set default'})
    warning_multiple_types_based_on_extra_hours = fields.Boolean(compute='_compute_warning_multiple_types_based_on_extra_hours')
    
    @api.depends('requires_allocation')
    def _compute_warning_multiple_types_based_on_extra_hours(self):
        for leave_type in self:
            if leave_type.requires_allocation != 'extra_hours':
                self.warning_multiple_types_based_on_extra_hours = False
            else:
                domain = [
                    ('company_id', 'in', self.env.company.ids + [False]),
                    ('requires_allocation', '=', 'extra_hours'),
                    ('id', 'not in', self.ids)
                ]
                leave_types = self.env['hr.leave.type'].search_count(domain)
                self.warning_multiple_types_based_on_extra_hours = leave_types >= 1

    @api.depends('requires_allocation')
    @api.depends_context('request_type', 'leave', 'holiday_status_display_name', 'employee_id')
    def _compute_display_name(self):
        # Exclude hours available in allocation contexts, it might be confusing otherwise
        if not self.requested_display_name() or self._context.get('request_type', 'leave') == 'allocation':
            return super()._compute_display_name()

        employee = self.env['hr.employee'].browse(self._context.get('employee_id')).sudo()
        if employee.total_overtime <= 0:
            return super()._compute_display_name()

        overtime_leaves = self.filtered(lambda l_type: l_type.requires_allocation == 'extra_hours')
        for leave_type in overtime_leaves:
            leave_type.display_name = "%(name)s (%(count)s)" % {
                'name': leave_type.name,
                'count': _('%s hours available',
                    format_duration(employee.total_overtime)),
            }
        super(HrLeaveType, self - overtime_leaves)._compute_display_name()

    def get_allocation_data(self, employees, date=None):
        res = super().get_allocation_data(employees, date)
        deductible_time_off_types = self.env['hr.leave.type'].search([
            ('requires_allocation', '=', 'extra_hours')])
        leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', employees.ids),
            ('holiday_status_id', 'in', deductible_time_off_types.ids),
            ('state', 'in', ['confirm', 'validate']),
        ])
        for employee in employees:
            for leave_type in deductible_time_off_types:
                confirmed_leaves = leaves.filtered(lambda l: l.employee_id == employee and l.holiday_status_id == leave_type and l.state == 'confirm')
                validated_leaves = leaves.filtered(lambda l: l.employee_id == employee and l.holiday_status_id == leave_type and l.state == 'validate')
                res[employee].append((leave_type.name, {
                    'remaining_leaves': 0,
                    'virtual_remaining_leaves': employee.sudo().total_overtime,
                    'max_leaves': 0,
                    'accrual_bonus': 0,
                    'leaves_taken': 0,
                    'virtual_leaves_taken': 0,
                    'leaves_requested': 0,
                    'leaves_approved': 0,
                    'closest_allocation_remaining': 0,
                    'closest_allocation_expire': False,
                    'holds_changes': False,
                    'total_virtual_excess': 0,
                    'virtual_excess_data': {},
                    'exceeding_duration': 0,
                    'request_unit': leave_type.request_unit,
                    'icon': leave_type.sudo().icon_id.url,
                    'allows_negative': leave_type.allows_negative,
                    'max_allowed_negative': leave_type.max_allowed_negative,
                    'employee_company': employee.company_id.id,
                    'closest_allocation_remaining': False,
                    'closest_allocation_expire': False,
                    'closest_allocation_duration': False,
                    'holds_changes': False,
                }, 'extra_hours', leave_type.id))
                for leave in confirmed_leaves:
                    if leave_type.request_unit == 'hour':
                        res[employee][-1][1]['leaves_requested'] += leave.number_of_hours
                    else:
                        res[employee][-1][1]['leaves_requested'] += leave.number_of_days
                for leave in validated_leaves:
                    if leave_type.request_unit == 'hour':
                        res[employee][-1][1]['leaves_approved'] += leave.number_of_hours
                    else:
                        res[employee][-1][1]['leaves_approved'] += leave.number_of_days
        return res

    def _get_days_request(self, date=None):
        res = super()._get_days_request(date)
        res[1]['overtime_deductible'] = self.requires_allocation == 'extra_hours'
        return res
