# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
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
    employee_overtime = fields.Float(related='employee_id.total_overtime', groups='base.group_user')

    @api.depends('holiday_status_id')
    def _compute_overtime_deductible(self):
        for allocation in self:
            allocation.overtime_deductible = allocation.holiday_status_id.overtime_deductible

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for allocation in res:
            if allocation.overtime_deductible:
                duration = allocation.number_of_hours_display
                if duration > allocation.employee_id.total_overtime:
                    raise ValidationError(_('The employee does not have enough overtime hours to request this leave.'))
                if not allocation.overtime_id:
                    allocation.sudo().overtime_id = self.env['hr.attendance.overtime'].sudo().create({
                        'employee_id': allocation.employee_id.id,
                        'date': allocation.date_from,
                        'adjustment': True,
                        'duration': -1 * duration,
                    })
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'number_of_days' not in vals:
            return res
        if not self.env.user.has_group("hr_holidays.group_hr_holidays_user") and any(allocation.state not in ('draft', 'confirm') for allocation in self):
            raise ValidationError(_('Only an Officer or Administrator is allowed to edit the allocation duration in this status.'))
        for allocation in self.sudo().filtered('overtime_id'):
            employee = allocation.employee_id
            duration = allocation.number_of_hours_display
            overtime_duration = allocation.overtime_id.sudo().duration
            if overtime_duration != -1 * duration:
                if duration > employee.total_overtime - overtime_duration:
                    raise ValidationError(_('The employee does not have enough extra hours to extend this allocation.'))
                allocation.overtime_id.sudo().duration = -1 * duration
        return res

    def action_refuse(self):
        res = super().action_refuse()
        self.overtime_id.sudo().unlink()
        return res

    def _get_accrual_plan_level_work_entry_prorata(self, level, start_period, start_date, end_period, end_date):
        self.ensure_one()
        if level.frequency != 'hourly' or level.frequency_hourly_source != 'attendance':
            return super()._get_accrual_plan_level_work_entry_prorata(level, start_period, start_date, end_period, end_date)
        datetime_min_time = datetime.min.time()
        start_dt = datetime.combine(start_date, datetime_min_time)
        end_dt = datetime.combine(end_date, datetime_min_time)
        attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', start_dt),
            ('check_out', '<=', end_dt),
        ])
        work_entry_prorata = sum(attendances.mapped('worked_hours'))
        return work_entry_prorata
