# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round

from odoo.addons.resource.models.resource import HOURS_PER_DAY


class HolidaysAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    overtime_deductible = fields.Boolean(compute='_compute_overtime_deductible')
    overtime_id = fields.Many2one('hr.attendance.overtime')
    employee_overtime = fields.Float(related='employee_id.total_overtime')
    hr_attendance_overtime = fields.Boolean(related='employee_id.hr_attendance_overtime')

    @api.depends('holiday_status_id')
    def _compute_overtime_deductible(self):
        deductibles = self.filtered(lambda a: a.holiday_status_id.company_id.hr_attendance_overtime and a.holiday_status_id.overtime_deductible)
        deductibles.overtime_deductible = True
        (self - deductibles).overtime_deductible = False

    def default_get(self, fields):
        res = super().default_get(fields)
        if 'holiday_status_id' in fields and self.env.context.get('deduct_extra_hours'):
            leave_type = self.env['hr.leave.type'].search([('valid', '=', True), ('overtime_deductible', '=', True), ('allocation_type', '!=', 'no')], limit=1)
            res['holiday_status_id'] = leave_type.id
        return res

    @api.model
    def create(self, vals):
        alloc_type = self.env['hr.leave.type'].browse(vals.get('holiday_status_id'))
        if alloc_type.company_id.hr_attendance_overtime and alloc_type.overtime_deductible and vals.get('holiday_type', 'employee') == 'employee':
            employee_sudo = self.env['hr.employee'].sudo().browse(vals.get('employee_id'))
            duration = float_round(vals.get('number_of_days') * employee_sudo.resource_calendar_id.hours_per_day or HOURS_PER_DAY, 2)
            if duration > employee_sudo.total_overtime:
                raise ValidationError(_('The employee has not enough extra hours to request this allocation.'))
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
            for allocation in self.filtered('overtime_id'):
                if allocation.number_of_days > num_days:
                    allocation.overtime_id.sudo().duration = -1 * float_round(num_days * allocation.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY, 2)
                elif allocation.number_of_days < num_days:
                    duration = float_round((num_days - allocation.number_of_days) * allocation.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY, 2)
                    if duration > allocation.employee_id.total_overtime:
                        raise ValidationError(_('The employee has not enough extra hours to extend this allocation.'))
                    allocation.overtime_id.sudo().duration -= duration
        return super().write(vals)

    def action_draft(self):
        overtimes = self.filtered('overtime_deductible')
        if any([a.employee_overtime < float_round(a.number_of_hours_display, 2) for a in overtimes]):
            raise ValidationError(_('The employee has not enough extra hours to request this allocation.'))
        res = super().action_draft()

        for allocation in overtimes:
            overtime = self.env['hr.attendance.overtime'].sudo().create({
                'employee_id': allocation.employee_id.id,
                'date': fields.Date.today(),
                'adjustment': True,
                'duration': -1 * allocation.number_of_hours_display
            })
            allocation.overtime_id = overtime.id
        return res

    def action_refuse(self):
        res = super().action_refuse()
        overtime_ids = self.filtered('overtime_deductible').overtime_id
        overtime_ids.sudo().unlink()
        return res
