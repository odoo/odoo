# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        today = fields.Date.today()
        for leave in res:
            if not leave.overtime_deductible:
                continue
            employee = leave.employee_id.sudo()
            duration = leave.number_of_hours_display
            if duration > employee.total_overtime:
                if employee.user_id == self.env.user:
                    raise ValidationError(_('You do not have enough extra hours to request this leave'))
                raise ValidationError(_('The employee does not have enough extra hours to request this leave.'))
            if not leave.overtime_id:
                leave.sudo().overtime_id = self.env['hr.attendance.overtime'].sudo().create({
                    'employee_id': employee.id,
                    'date': today,
                    'adjustment': True,
                    'duration': -1 * duration,
                })
        return res

    def write(self, vals):
        res = super().write(vals)
        fields_to_check = {'number_of_days', 'date_from', 'date_to', 'state', 'employee_id'}
        if not any(field for field in fields_to_check if field in vals):
            return res
        #User may not have access to overtime_id field
        for leave in self.sudo().filtered('overtime_id'):
            employee = leave.employee_id
            duration = leave.number_of_hours_display
            overtime_duration = leave.overtime_id.sudo().duration
            if overtime_duration != duration:
                if duration > employee.total_overtime - overtime_duration:
                    raise ValidationError(_('The employee does not have enough extra hours to extend this leave.'))
                leave.overtime_id.sudo().duration = -1 * duration
        return res

    def action_draft(self):
        overtime_leaves = self.filtered('overtime_deductible')
        if any([l.employee_overtime < float_round(l.number_of_hours_display, 2) for l in overtime_leaves]):
            if self.employee_id.user_id.id == self.env.user.id:
                raise ValidationError(_('You do not have enough extra hours to request this leave'))
            raise ValidationError(_('The employee does not have enough extra hours to request this leave.'))

        res = super().action_draft()
        overtime_leaves.overtime_id.sudo().unlink()
        for leave in overtime_leaves:
            overtime = self.env['hr.attendance.overtime'].sudo().create({
                'employee_id': leave.employee_id.id,
                'date': fields.Date.today(),
                'adjustment': True,
                'duration': -1 * leave.number_of_hours_display
            })
            leave.sudo().overtime_id = overtime.id
        return res

    def action_refuse(self):
        res = super().action_refuse()
        self.overtime_id.sudo().unlink()
        return res
