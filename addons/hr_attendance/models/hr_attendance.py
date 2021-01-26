# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero, float_round


class HrAttendance(models.Model):
    _name = "hr.attendance"
    _description = "Attendance"
    _order = "check_in desc"

    def _default_employee(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True, ondelete='cascade', index=True)
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",
        readonly=True)
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=True)
    check_out = fields.Datetime(string="Check Out")
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)

    def name_get(self):
        result = []
        for attendance in self:
            if not attendance.check_out:
                result.append((attendance.id, _("%(empl_name)s from %(check_in)s") % {
                    'empl_name': attendance.employee_id.name,
                    'check_in': format_datetime(self.env, attendance.check_in, dt_format=False),
                }))
            else:
                result.append((attendance.id, _("%(empl_name)s from %(check_in)s to %(check_out)s") % {
                    'empl_name': attendance.employee_id.name,
                    'check_in': format_datetime(self.env, attendance.check_in, dt_format=False),
                    'check_out': format_datetime(self.env, attendance.check_out, dt_format=False),
                }))
        return result

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out:
                delta = attendance.check_out - attendance.check_in
                attendance.worked_hours = delta.total_seconds() / 3600.0
            else:
                attendance.worked_hours = False

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out. """
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['hr.attendance'].search([
                ('employee_id', '=', attendance.employee_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
                raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                    'empl_name': attendance.employee_id.name,
                    'datetime': format_datetime(self.env, attendance.check_in, dt_format=False),
                })

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if no_check_out_attendances:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s") % {
                        'empl_name': attendance.employee_id.name,
                        'datetime': format_datetime(self.env, no_check_out_attendances.check_in, dt_format=False),
                    })
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                        'empl_name': attendance.employee_id.name,
                        'datetime': format_datetime(self.env, last_attendance_before_check_out.check_in, dt_format=False),
                    })

    def _get_attendances_dates(self):
        attendances_emp = defaultdict(set)
        for attendance in self.filtered(lambda a: a.employee_id.company_id.hr_attendance_overtime and a.check_in and a.check_in.date() >= a.employee_id.company_id.overtime_start_date and a.check_out):
            attendances_emp[attendance.employee_id].add(attendance.check_in.date())
            attendances_emp[attendance.employee_id].add(attendance.check_out.date())
        return attendances_emp

    def _update_overtime(self, dates=None):
        if dates is None:
            dates = self._get_attendances_dates()

        overtime_unlink = self.env['hr.attendance.overtime']
        overtime_create = []
        for emp, days in dates.items():
            domain = []
            for day in days:
                start = datetime.combine(day, datetime.min.time())
                stop = datetime.combine(day, datetime.max.time())
                domain = OR([domain, [
                    '&', ('check_in', '>=', start), ('check_in', '<=', stop),
                ]])

            domain = AND([[('employee_id', '=', emp.id)], domain])
            day_attendances = defaultdict(self.browse)
            all_attendances = self.env['hr.attendance'].search(domain)
            for attendance in all_attendances:
                day_attendances[attendance.check_in.date()] += attendance

            start = datetime.combine(min(days), datetime.min.time())
            stop = datetime.combine(max(days), datetime.max.time())
            working_times = {x[0]: x[1] for x in emp.list_work_time_per_day(start, stop)}
            overtimes = self.env['hr.attendance.overtime'].sudo().search([
                ('employee_id', '=', emp.id),
                ('date', 'in', list(days)),
                ('adjustment', '=', False),
            ])

            for day in days:
                attendances = day_attendances.get(day, self.browse())
                worked = sum(attendances.mapped('worked_hours'))
                work_time = working_times.get(day, 0)
                overtime = overtimes.filtered(lambda o: o.date == day)
                ot_duration = float_round(worked - work_time, 2)
                if not float_is_zero(ot_duration, 2):
                    if not overtime:
                        overtime_create.append({
                            'employee_id': emp.id,
                            'date': day,
                            'duration': ot_duration,
                        })
                    else:
                        overtime.write({'duration': ot_duration})
                elif overtime:
                    overtime_unlink |= overtime
        self.env['hr.attendance.overtime'].sudo().create(overtime_create)
        overtime_unlink.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._update_overtime()
        return res

    def write(self, vals):
        previous_attendances_dates = self._get_attendances_dates()
        super(HrAttendance, self).write(vals)
        if any(check in vals for check in ['employee_id', 'check_in', 'check_out']):
            attendances_dates = {**previous_attendances_dates, **self._get_attendances_dates()}
            self._update_overtime(attendances_dates)

    def unlink(self):
        attendances_dates = self._get_attendances_dates()
        super(HrAttendance, self).unlink()
        self._update_overtime(attendances_dates)

    @api.returns('self', lambda value: value.id)
    def copy(self):
        raise exceptions.UserError(_('You cannot duplicate an attendance.'))
