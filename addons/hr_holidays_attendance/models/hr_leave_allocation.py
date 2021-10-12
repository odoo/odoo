# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round
from odoo.osv import expression


class HolidaysAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    def default_get(self, fields):
        res = super().default_get(fields)
        if 'holiday_status_id' in fields and self.env.context.get('deduct_extra_hours'):
            domain = [('overtime_deductible', '=', True), ('requires_allocation', '=', 'yes')]
            if self.env.context.get('deduct_extra_hours_employee_request', False):
                # Prevent loading manager allocated time off type in self request contexts
                domain = expression.AND([domain, [('employee_requests', '=', 'yes')]])
            leave_type = self.env['hr.leave.type'].search(domain, limit=1)
            res['holiday_status_id'] = leave_type.id
        return res

    overtime_deductible = fields.Boolean(compute='_compute_overtime_deductible')
    overtime_id = fields.Many2one('hr.attendance.overtime', string='Extra Hours', groups='hr_holidays.group_hr_holidays_user')
    employee_overtime = fields.Float(related='employee_id.total_overtime')
    hr_attendance_overtime = fields.Boolean(related='employee_company_id.hr_attendance_overtime')

    @api.depends('holiday_status_id')
    def _compute_overtime_deductible(self):
        for allocation in self:
            allocation.overtime_deductible = allocation.hr_attendance_overtime and allocation.holiday_status_id.overtime_deductible

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for allocation in res:
            if allocation.overtime_deductible and allocation.holiday_type == 'employee':
                duration = allocation.number_of_hours_display
                if duration > allocation.employee_id.total_overtime:
                    raise ValidationError(_('The employee does not have enough overtime hours to request this leave.'))
                if not allocation.overtime_id:
                    allocation.sudo().overtime_id = self.env['hr.attendance.overtime'].sudo().create({
                        'employee_id': allocation.employee_id.id,
                        'date': fields.Date.today(),
                        'adjustment': True,
                        'duration': -1 * duration,
                    })
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'number_of_days' not in vals:
            return res
        for allocation in self.filtered('overtime_id'):
            employee = allocation.employee_id
            duration = allocation.number_of_hours_display
            overtime_duration = allocation.overtime_id.sudo().duration
            if overtime_duration != duration:
                if duration > employee.total_overtime - overtime_duration:
                    raise ValidationError(_('The employee does not have enough extra hours to extend this allocation.'))
                allocation.overtime_id.sudo().duration = -1 * duration
        return res

    def action_draft(self):
        overtime_allocations = self.filtered('overtime_deductible')
        if any([a.employee_overtime < float_round(a.number_of_hours_display, 2) for a in overtime_allocations]):
            raise ValidationError(_('The employee does not have enough extra hours to request this allocation.'))
        res = super().action_draft()

        overtime_allocations.overtime_id.sudo().unlink()
        for allocation in overtime_allocations:
            overtime = self.env['hr.attendance.overtime'].sudo().create({
                'employee_id': allocation.employee_id.id,
                'date': fields.Date.today(),
                'adjustment': True,
                'duration': -1 * allocation.number_of_hours_display
            })
            allocation.sudo().overtime_id = overtime.id
        return res

    def action_refuse(self):
        res = super().action_refuse()
        self.overtime_id.sudo().unlink()
        return res
