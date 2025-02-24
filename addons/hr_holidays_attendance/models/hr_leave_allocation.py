# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    overtime_deductible = fields.Boolean(compute='_compute_overtime_deductible')
    overtime_id = fields.Many2one('hr.attendance.overtime', string='Extra Hours', groups='hr_holidays.group_hr_holidays_user')
    employee_overtime = fields.Float(related='employee_id.total_overtime', groups='base.group_user')

    @api.depends('holiday_status_id')
    def _compute_overtime_deductible(self):
        for allocation in self:
            allocation.overtime_deductible = allocation.holiday_status_id.requires_allocation == 'extra_hours'

    @api.model_create_multi
    def create(self, vals_list):
        allocations = super().create(vals)
        extra_hours_allocation = self.env['hr.leave.allocation']
        for allocation in allocations:
            if allocation.holiday_status_id.requires_allocation == 'extra_hours':
                extra_hours_allocation += allocation
        if extra_hours_allocation:
            raise ValidationError(
                _("You cannot create an allocation request for the following allocations. Because their leave type are based on extra hours. %s",
                "\n".join(allocation.name for allocation in extra_hours_allocation)))
        return allocations

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
    
    def create(self, vals):
        records = super().create(vals)
        for record in records:
            if record.holiday_status_id.requires_allocation == 'extra_hours':
                raise ValidationError(_('You cannot create an allocation request for a leave type based on extra hours.'))
        return records
