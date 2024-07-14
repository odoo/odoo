#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
from collections import defaultdict

from odoo import api, models
from odoo.fields import Datetime

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def _get_employee_calendar(self):
        self.ensure_one()
        contracts = self.employee_id.sudo()._get_contracts(self.check_in, self.check_out, states=['open', 'close'])
        if contracts:
            return contracts[0].resource_calendar_id
        return super()._get_employee_calendar()

    def _create_work_entries(self):
        # Upon creating or closing an attendance, create the work entry directly if the attendance
        # was created within an already generated period
        # This code assumes that attendances are not created/written in big batches
        work_entries_vals_list = []
        for attendance in self:
            # Filter closed attendances
            if not attendance.check_out:
                continue
            contracts = attendance.employee_id.sudo()._get_contracts(
                attendance.check_in, attendance.check_out, states=['open', 'close'])
            for contract in contracts:
                if attendance.check_out >= contract.date_generated_from and attendance.check_in <= contract.date_generated_to:
                    work_entries_vals_list += contracts._get_work_entries_values(
                        datetime.combine(attendance.check_in, time.min),
                        datetime.combine(attendance.check_out, time.max))
        if work_entries_vals_list:
            new_work_entries = self.env['hr.work.entry'].sudo().create(work_entries_vals_list)
            if new_work_entries:
                # Fetch overlapping work entries, grouped by employees
                start = min((datetime.combine(a.check_in, time.min) for a in self if a.check_in), default=False)
                stop = max((datetime.combine(a.check_out, time.max) for a in self if a.check_out), default=False)
                work_entry_groups = self.env['hr.work.entry'].sudo()._read_group([
                    ('date_start', '<', stop),
                    ('date_stop', '>', start),
                    ('employee_id', 'in', self.employee_id.ids),
                ], ['employee_id'], ['id:recordset'])
                work_entries_by_employee = {
                    employee.id: records
                    for employee, records in work_entry_groups
                }

                # Archive work entries included in new work entries
                included = self.env['hr.work.entry']
                overlappping = self.env['hr.work.entry']
                for work_entries in work_entries_by_employee.values():
                    # Work entries for this employee
                    new_employee_work_entries = work_entries & new_work_entries
                    previous_employee_work_entries = work_entries - new_work_entries

                    # Build intervals from work entries
                    attendance_intervals = new_employee_work_entries._to_intervals()
                    conflicts_intervals = previous_employee_work_entries._to_intervals()

                    # Compute intervals completely outside any attendance
                    # Intervals are outside, but associated records are overlapping.
                    outside_intervals = conflicts_intervals - attendance_intervals

                    overlappping |= self.env['hr.work.entry']._from_intervals(outside_intervals)
                    included |= previous_employee_work_entries - overlappping
                overlappping.sudo().write({'attendance_id': False})
                included.sudo().write({'active': False})

    @api.model_create_multi
    def create(self, vals_list):
        start_dates = [v.get('check_in') for v in vals_list if v.get('check_in')]
        stop_dates = [v.get('check_out') for v in vals_list if v.get('check_out')]
        res = super().create(vals_list)
        with self.env['hr.work.entry']._error_checking(start=min(start_dates, default=False), stop=max(stop_dates, default=False), employee_ids=res.employee_id.ids):
            res._create_work_entries()
        return res

    def write(self, vals):
        new_check_out = vals.get('check_out')
        open_attendances = self.filtered(lambda a: not a.check_out) if new_check_out else self.env['hr.attendance']
        res = super().write(vals)
        if not open_attendances:
            return res
        skip_check = not bool({'check_in', 'check_out', 'employee_id'} & vals.keys())
        start = min(self.mapped('check_in') + [Datetime.from_string(vals.get('check_in', False)) or datetime.max])
        stop = max(self.mapped('check_out') + [Datetime.from_string(vals.get('check_out', False)) or datetime.min])
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop, skip=skip_check, employee_ids=self.employee_id.ids):
            open_attendances._create_work_entries()
        return res

    def unlink(self):
        # Archive linked work entries upon deleting attendances
        self.env['hr.work.entry'].sudo().search([('attendance_id', 'in', self.ids)]).write({'active': False})
        start_dates = [a.check_in for a in self if a.check_in]
        stop_dates = [a.check_out for a in self if a.check_out]
        with self.env['hr.work.entry']._error_checking(start=min(start_dates, default=False), stop=max(stop_dates, default=False), employee_ids=self.employee_id.ids):
            res = super().unlink()
        return res
