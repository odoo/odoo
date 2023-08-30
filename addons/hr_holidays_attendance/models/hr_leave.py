# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class HRLeave(models.Model):
    _inherit = 'hr.leave'

    overtime_id = fields.Many2one('hr.attendance.overtime', string='Extra Hours', groups='hr_holidays.group_hr_holidays_user')
    employee_overtime = fields.Float(related='employee_id.total_overtime')
    overtime_deductible = fields.Boolean(compute='_compute_overtime_deductible')

    @api.depends('holiday_status_id')
    def _compute_overtime_deductible(self):
        for leave in self:
            leave.overtime_deductible = leave.holiday_status_id.overtime_deductible and leave.holiday_status_id.requires_allocation == 'no'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self._check_overtime_deductible(res)
        return res

    def write(self, vals):
        res = super().write(vals)
        fields_to_check = {'number_of_days', 'date_from', 'date_to', 'state', 'employee_id', 'holiday_status_id'}
        if not any(field for field in fields_to_check if field in vals):
            return res
        self._check_overtime_deductible(self)
        return res

    def _check_overtime_deductible(self, leaves):
        # This method manage checks to consume overtime
        # to create/write/unlink `hr.attendance.overtime` on leaves
        for leave in leaves:
            leave = leave.sudo()
            # [1] Check if overtime_deductible and the state (if `holiday_status_id` changes)
            if not leave.overtime_deductible or leave.state == 'refuse':
                if leave.overtime_id:
                    leave.overtime_id.unlink()
                continue
            # [2] Check if the employee have enough overtime
            employee = leave.employee_id
            employee_overtime = employee.total_overtime
            leave_duration = leave.number_of_hours_display
            if leave.overtime_id:
                # If there is an existing overtime that we may have to modify its duration,
                # we have to add its duration because we have to compare all overtimes of the employee
                # with the duration of the leave we are modifying.
                employee_overtime += -1 * leave.overtime_id.duration
            if leave_duration > employee_overtime:
                if employee.user_id == self.env.user:
                    raise ValidationError(_('You do not have enough extra hours to request this leave'))
                raise ValidationError(_('The employee does not have enough extra hours to request this leave.'))
            # [3] All checks are validated we can apply information on the overtime_id
            if not leave.overtime_id:
                leave.overtime_id = self.env['hr.attendance.overtime'].sudo().create({
                    'employee_id': employee.id,
                    'date': leave.date_from,
                    'adjustment': True,
                    'duration': -1 * leave_duration,
                })
            else:
                leave.overtime_id.write({
                    'date': leave.date_from,
                    'adjustment': True,
                    'duration': -1 * leave_duration,
                })

    def action_draft(self):
        res = super().action_draft()
        self._check_overtime_deductible(self)
        return res

    def action_refuse(self):
        res = super().action_refuse()
        self._check_overtime_deductible(self)
        return res

    def _validate_leave_request(self):
        super()._validate_leave_request()
        self._update_leaves_overtime()

    def _remove_resource_leave(self):
        res = super()._remove_resource_leave()
        self._update_leaves_overtime()
        return res

    def _update_leaves_overtime(self):
        employee_dates = defaultdict(set)
        for leave in self:
            if leave.employee_id and leave.employee_company_id.hr_attendance_overtime:
                for d in range((leave.date_to - leave.date_from).days + 1):
                    employee_dates[leave.employee_id].add(self.env['hr.attendance']._get_day_start_and_day(leave.employee_id, leave.date_from + timedelta(days=d)))
        if employee_dates:
            self.env['hr.attendance']._update_overtime(employee_dates)

    def unlink(self):
        # TODO master change to ondelete
        self.sudo().overtime_id.unlink()
        return super().unlink()
