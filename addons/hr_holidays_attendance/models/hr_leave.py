# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round

from odoo.addons.resource.models.resource import HOURS_PER_DAY


class HRLeave(models.Model):
    _inherit = 'hr.leave'

    overtime_id = fields.Many2one('hr.attendance.overtime', string='Extra Hours')
    employee_overtime = fields.Float(related='employee_id.total_overtime')
    overtime_deductible = fields.Boolean(compute='_compute_overtime_deductible')

    @api.depends('holiday_status_id')
    def _compute_overtime_deductible(self):
        self.overtime_deductible = False
        deductibles = self.filtered(lambda l: l.holiday_status_id.overtime_deductible and l.holiday_status_id.allocation_type == 'no')
        deductibles.overtime_deductible = True

    @api.model
    def create(self, vals):
        leave_type = self.env['hr.leave.type'].browse(vals.get('holiday_status_id'))
        if leave_type.overtime_deductible and leave_type.allocation_type == 'no':
            employee_sudo = self.env['hr.employee'].sudo().browse(vals.get('employee_id'))
            duration = float_round(vals.get('number_of_days') * employee_sudo.resource_calendar_id.hours_per_day or HOURS_PER_DAY, 2)
            if duration > employee_sudo.total_overtime:
                raise ValidationError(_('The employee has not enough extra hours to request this leave.'))

            if not vals.get('overtime_id'):
                overtime_id = self.env['hr.attendance.overtime'].sudo().create({
                    'employee_id': employee_sudo.id,
                    'date': fields.Date.today(),
                    'adjustment': True,
                    'duration': -1 * duration,
                })
                vals['overtime_id'] = overtime_id.id

        return super().create(vals)

    def write(self, vals):
        if 'number_of_days' in vals:
            num_days = vals['number_of_days']
            for leave in self.filtered('overtime_id'):
                if leave.number_of_days > num_days:
                    leave.overtime_id.sudo().duration = -1 * float_round(num_days * leave.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY, 2)
                elif leave.number_of_days < num_days:
                    duration = float_round((num_days - leave.number_of_days) * leave.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY, 2)
                    if duration > leave.employee_id.total_overtime:
                        raise ValidationError(_('The employee has not enough extra hours to extend this leave.'))
                    leave.overtime_id.sudo().duration -= duration
        return super().write(vals)

    def action_draft(self):
        overtimes = self.filtered('overtime_deductible')
        if any([l.employee_overtime < float_round(l.number_of_hours_display, 2) for l in overtimes]):
            raise ValidationError(_('The employee has not enough extra hours to request this leave.'))

        res = super().action_draft()
        for leave in overtimes:
            overtime = self.env['hr.attendance.overtime'].sudo().create({
                'employee_id': leave.employee_id.id,
                'date': fields.Date.today(),
                'adjustment': True,
                'duration': -1 * leave.number_of_hours_display
            })
            leave.overtime_id = overtime.id
        return res

    def action_refuse(self):
        res = super().action_refuse()
        overtime_ids = self.filtered('overtime_deductible').overtime_id
        overtime_ids.sudo().unlink()
        return res
