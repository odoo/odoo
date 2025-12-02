# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    employee_overtime = fields.Float(compute='_compute_employee_overtime', groups='base.group_user')
    overtime_deductible = fields.Boolean(compute='_compute_overtime_deductible')

    @api.depends('holiday_status_id')
    def _compute_overtime_deductible(self):
        for leave in self:
            leave.overtime_deductible = leave.holiday_status_id.overtime_deductible and not leave.holiday_status_id.requires_allocation

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
        self._check_overtime_deductible(self)
        return res

    @api.model
    def _get_deductible_employee_overtime(self, employees):
        # return dict {employee: number of hours}
        diff_by_employee = defaultdict(lambda: 0)
        for employee, hours in self.env['hr.attendance.overtime.line'].sudo()._read_group(
            domain=[
                ('compensable_as_leave', '=', True),
                ('employee_id', 'in', employees.ids),
                ('status', '=', 'approved'),
            ],
            groupby=['employee_id'],
            aggregates=['manual_duration:sum'],
        ):
            diff_by_employee[employee] += hours
        for employee, hours in self._read_group(
            domain=[
                ('holiday_status_id.overtime_deductible', '=', True),
                ('holiday_status_id.requires_allocation', '=', False),
                ('employee_id', 'in', employees.ids),
                ('state', 'not in', ['refuse', 'cancel']),
            ],
            groupby=['employee_id'],
            aggregates=['number_of_hours:sum'],
        ):
            diff_by_employee[employee] -= hours
        for employee, hours in self.env['hr.leave.allocation']._read_group(
            domain=[
                ('holiday_status_id.overtime_deductible', '=', True),
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'confirm'),
            ],
            groupby=['employee_id'],
            aggregates=['number_of_hours_display:sum'],
        ):
            diff_by_employee[employee] -= hours
        return diff_by_employee

    @api.depends('number_of_hours', 'employee_id', 'holiday_status_id')
    def _compute_employee_overtime(self):
        diff_by_employee = self._get_deductible_employee_overtime(self.employee_id)
        for leave in self:
            leave.employee_overtime = diff_by_employee[leave.employee_id]

    def _check_overtime_deductible(self, leaves):
        # If the type of leave is overtime deductible, we have to check that the employee has enough extra hours
        hours = self._get_deductible_employee_overtime(leaves.employee_id)
        for leave in leaves.filtered('overtime_deductible'):
            if hours[leave.employee_id] < 0:
                if leave.employee_id.user_id == self.env.user:
                    raise ValidationError(_('You do not have enough extra hours to request this leave'))
                raise ValidationError(_('The employee does not have enough extra hours to request this leave.'))

    def action_reset_confirm(self):
        self._check_overtime_deductible(self)
        res = super().action_reset_confirm()
        return res

    def action_approve(self, check_state=True):
        res = super().action_approve(check_state)
        self._check_overtime_deductible(self)
        return res

    def action_refuse(self):
        res = super().action_refuse()
        return res

    def _validate_leave_request(self):
        super()._validate_leave_request()
        self._update_leaves_overtime()

    def _remove_resource_leave(self):
        res = super()._remove_resource_leave()
        self._update_leaves_overtime()
        return res

    def _update_leaves_overtime(self):
        Attendance = self.env['hr.attendance']
        dates = [
            Attendance._attendance_date(leave.date_from, leave.employee_id)
            for leave in self.filtered(lambda leave: leave.state == 'confirmed')
        ]
        if dates:
            Attendance.search([
                ('date', '>=', min(dates)),
                ('date', '<=', max(dates)),
                ('employee_id', 'in', self.employee_id.ids),
            ])._update_overtimes()

    def _force_cancel(self, *args, **kwargs):
        super()._force_cancel(*args, **kwargs)
