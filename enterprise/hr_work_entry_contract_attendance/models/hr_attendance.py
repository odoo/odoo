#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time, timedelta
from collections import defaultdict
from odoo.exceptions import UserError

from odoo import api, models, _
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
                    start_stamp, start_date = attendance.check_in, attendance.check_in.date()
                    end_stamp, end_date = attendance.check_out, attendance.check_out.date()

                    if start_date == end_date:
                        day_bounds = datetime.combine(start_date, time.min), datetime.combine(start_date, time.max)
                        work_entries_vals_list += contract._get_work_entries_values(*day_bounds)
                    else:
                        work_entries_vals_list += contract._get_work_entries_values(start_stamp, datetime.combine(start_date, time.max))
                        date_cursor = start_date + timedelta(days=1)
                        while date_cursor < end_date:
                            bounds = datetime.combine(date_cursor, time.min), datetime.combine(date_cursor, time.max)
                            work_entries_vals_list += contract._get_work_entries_values(*bounds)
                            date_cursor += timedelta(days=1)
                        work_entries_vals_list += contract._get_work_entries_values(datetime.combine(end_date, time.min), end_stamp)

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
        validated_work_entries = self.env['hr.work.entry'].sudo().search([('attendance_id', 'in', self.ids), ('state', '=', 'validated')])
        if validated_work_entries:
            raise UserError(_("This attendance record is linked to a validated working entry. You can't modify it."))
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

    @api.ondelete(at_uninstall=False)
    def _unlink_except_validated_work_entries(self):
        validated_work_entries = self.env['hr.work.entry'].sudo().search([('attendance_id', 'in', self.ids), ('state', '=', 'validated')])
        if validated_work_entries:
            raise UserError(_("This attendance record is linked to a validated working entry. You can't delete it."))

    def unlink(self):
        # Archive linked work entries upon deleting attendances
        self.env['hr.work.entry'].sudo().search([('attendance_id', 'in', self.ids)]).write({'active': False})
        start_dates = [a.check_in for a in self if a.check_in]
        stop_dates = [a.check_out for a in self if a.check_out]
        with self.env['hr.work.entry']._error_checking(start=min(start_dates, default=False), stop=max(stop_dates, default=False), employee_ids=self.employee_id.ids):
            res = super().unlink()
        return res
