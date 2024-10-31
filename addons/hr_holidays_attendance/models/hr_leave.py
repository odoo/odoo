# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class HRLeave(models.Model):
    _inherit = 'hr.leave'

    overtime_id = fields.Many2one('hr.attendance.overtime', string='Extra Hours')
    employee_overtime = fields.Float(related='employee_id.total_overtime', groups='base.group_user')
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
        fields_to_check = {'number_of_days', 'request_date_from', 'request_date_to', 'state', 'employee_id', 'holiday_status_id'}
        if not any(field for field in fields_to_check if field in vals):
            return res
        if vals.get('holiday_status_id'):
            self._check_overtime_deductible(self)
        #User may not have access to overtime_id field
        for leave in self.sudo().filtered('overtime_id'):
            # It must always be possible to refuse leave based on overtime
            if vals.get('state') in ['refuse']:
                continue
            employee = leave.employee_id
            duration = leave.number_of_hours
            overtime_duration = leave.overtime_id.sudo().duration
            if overtime_duration != -1 * duration:
                if duration > employee.total_overtime - overtime_duration:
                    raise ValidationError(_('The employee does not have enough extra hours to extend this leave.'))
                leave.overtime_id.sudo().duration = -1 * duration
        return res

    def _check_overtime_deductible(self, leaves):
        # If the type of leave is overtime deductible, we have to check that the employee has enough extra hours
        for leave in leaves:
            if not leave.overtime_deductible:
                continue
            employee = leave.employee_id.sudo()
            duration = leave.number_of_hours
            if duration > employee.total_overtime:
                if employee.user_id == self.env.user:
                    raise ValidationError(_('You do not have enough extra hours to request this leave'))
                raise ValidationError(_('The employee does not have enough extra hours to request this leave.'))
            if not leave.sudo().overtime_id:
                leave.sudo().overtime_id = self.env['hr.attendance.overtime'].sudo().create({
                    'employee_id': employee.id,
                    'date': leave.date_from,
                    'adjustment': True,
                    'duration': -1 * duration,
                })

    def action_draft(self):
        overtime_leaves = self.filtered('overtime_deductible')
        res = super().action_draft()
        overtime_leaves.overtime_id.sudo().unlink()
        return res

    def action_confirm(self):
        res = super().action_confirm()
        self._check_overtime_deductible(self)
        return res

    def action_refuse(self):
        res = super().action_refuse()
        self.sudo().overtime_id.unlink()
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
            self.env['hr.attendance'].sudo()._update_overtime(employee_dates)

    def unlink(self):
        # TODO master change to ondelete
        self.sudo().overtime_id.unlink()
        return super().unlink()

    def _force_cancel(self, *args, **kwargs):
        super()._force_cancel(*args, **kwargs)
        self.sudo().overtime_id.unlink()
