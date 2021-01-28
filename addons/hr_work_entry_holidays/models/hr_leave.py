# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, date
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.resource.models.resource import Intervals


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Work Entry Type')


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _get_new_resource_leave_values(self):
        """
        This method aims to be overriden when resource values are depending on employee contract.
        :return: resource_leave_values to be created by _create_resource_leave
        """
        self.ensure_one()
        calendar = self._get_calendar()
        return [{
            'name': _("%s: Time Off", self.employee_id.name),
            'holiday_id': self.id,
            'resource_id': self.employee_id.resource_id.id,
            'work_entry_type_id': self.holiday_status_id.work_entry_type_id.id,
            'time_type': self.holiday_status_id.time_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'calendar_id': calendar.id,
        }]

    def _create_resource_leave(self):
        """
        Add a resource leave in calendars of contracts running at the same period.
        This is needed in order to compute the correct number of hours/days of the leave
        according to the company working hours or contract's calender.
        """
        resource_leaves = super(HrLeave, self)._create_resource_leave()
        for resource_leave in resource_leaves:
            resource_leave.work_entry_type_id = resource_leave.holiday_id.holiday_status_id.work_entry_type_id.id

        resource_leave_values = []

        for leave in self.filtered(lambda l: l.employee_id):
            value = leave._get_new_resource_leave_values()
            if value:
                resource_leave_values += value

        return resource_leaves | self.env['resource.calendar.leaves'].create(resource_leave_values)

    def _get_work_entry_values(self):
        """
        This method return work-entry values based on the leave values.
        :return: work entry list of new values.
        """
        work_entries_vals_list = []
        for leave in self:
            # We create a work entry according to company working hours.
            # For more accuracy, one must install hr_holidays_contract to generate work entry depending on the employee
            # details.
            holiday_status_id = leave.holiday_status_id
            work_entry_type_id = holiday_status_id.work_entry_type_id
            start_tz = pytz.timezone(leave.employee_id.tz).localize(leave.date_from)
            stop_tz = pytz.timezone(leave.employee_id.tz).localize(leave.date_to)
            calendar = leave.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
            attendances = calendar._attendance_intervals_batch(start_tz, stop_tz)
            default_vals = {
                    'name': "%s: %s" % (work_entry_type_id.name, leave.employee_id.name),
                    'work_entry_type_id': work_entry_type_id.id,
                    'employee_id': leave.employee_id.id,
                    'company_id': leave.employee_id.company_id.id,
                    'state': 'validated',
                    'leave_id': leave.id,
            }

            for att in attendances[False]._items:
                # arj fixme wtf ??
                # what if true?
                vals_copy = default_vals.copy()
                vals_copy.update(
                    {'date_start': att[0].astimezone(pytz.utc).replace(tzinfo=None),
                     'date_stop': att[1].astimezone(pytz.utc).replace(tzinfo=None)}
                )
                work_entries_vals_list += [vals_copy]
        return work_entries_vals_list

    def _cancel_work_entry_conflict(self):
        """
        Creates a leave work entry for each hr.leave in self.
        Check overlapping work entries with self.
        Work entries completely included in a leave are archived.
        e.g.:
            |----- work entry ----|---- work entry ----|
                |------------------- hr.leave ---------------|
                                    ||
                                    vv
            |----* work entry ****|
                |************ work entry leave --------------|
        """
        if not self:
            return
        # 1. Create a work entry for each leave according to company attendance_ids
        work_entries_vals_list = self._get_work_entry_values()
        new_leave_work_entries = self.env['hr.work.entry'].create(work_entries_vals_list)

        if new_leave_work_entries:
            # 2. Fetch overlapping work entries, grouped by employees
            start = min(self.mapped('date_from'), default=False)
            stop = max(self.mapped('date_to'), default=False)
            work_entry_groups = self.env['hr.work.entry'].read_group([
                ('date_start', '<', stop),
                ('date_stop', '>', start),
                ('employee_id', 'in', self.employee_id.ids),
            ], ['work_entry_ids:array_agg(id)', 'employee_id'], ['employee_id', 'date_start', 'date_stop'], lazy=False)
            work_entries_by_employee = defaultdict(lambda: self.env['hr.work.entry'])
            for group in work_entry_groups:
                employee_id = group.get('employee_id')[0]
                work_entries_by_employee[employee_id] |= self.env['hr.work.entry'].browse(group.get('work_entry_ids'))

            # 3. Archive work entries included in leaves
            included = self.env['hr.work.entry']
            overlappping = self.env['hr.work.entry']
            for work_entries in work_entries_by_employee.values():
                # Work entries for this employee
                new_employee_work_entries = work_entries & new_leave_work_entries
                previous_employee_work_entries = work_entries - new_leave_work_entries

                # Build intervals from work entries
                leave_intervals = self._get_work_entry_to_intervals(new_employee_work_entries)
                conflicts_intervals = self._get_work_entry_to_intervals(previous_employee_work_entries)
                # Compute intervals completely outside any leave
                # Intervals are outside, but associated records are overlapping.
                outside_intervals = conflicts_intervals - leave_intervals

                overlappping |= self.env['hr.work.entry']._from_intervals(outside_intervals)
                included |= previous_employee_work_entries - overlappping
            overlappping.write({'leave_id': False})
            included.write({'active': False})

    def _get_work_entry_to_intervals(self, work_entry):
        return Intervals(
            Intervals((w.date_start.replace(tzinfo=pytz.utc), w.date_stop.replace(tzinfo=pytz.utc), w) for w in work_entry)
        )

    def write(self, vals):
        if not self:
            return True
        skip_check = not bool({'employee_id', 'state', 'date_from', 'date_to'} & vals.keys())

        start = min(self.mapped('date_from') + [fields.Datetime.from_string(vals.get('date_from', False)) or datetime.max])
        stop = max(self.mapped('date_to') + [fields.Datetime.from_string(vals.get('date_to', False)) or datetime.min])
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop, skip=skip_check):
            return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        start_dates = [v.get('date_from') for v in vals_list if v.get('date_from')]
        stop_dates = [v.get('date_to') for v in vals_list if v.get('date_to')]
        if any(vals.get('holiday_type', 'employee') == 'employee' and not vals.get('employee_id', False) for vals in vals_list):
            raise ValidationError(_("There is no employee set on the time off. Please make sure you're logged in the correct company."))
        with self.env['hr.work.entry']._error_checking(start=min(start_dates, default=False), stop=max(stop_dates, default=False)):
            return super().create(vals_list)

    def action_confirm(self):
        start = min(self.mapped('date_from'), default=False)
        stop = max(self.mapped('date_to'), default=False)
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop):
            return super().action_confirm()

    def action_validate(self):
        super(HrLeave, self).action_validate()
        self.sudo()._cancel_work_entry_conflict()  # delete preexisting conflicting work_entries
        return True

    def _refused_work_entry(self, work_entries):
        attendance = self.env.ref('hr_work_entry.work_entry_type_attendance')
        for we in work_entries:
            new_work_entry = we.copy()
            name = _("%s: %s", attendance.name, work_entries.employee_id.name)
            new_work_entry.write({'active': True, 'leave_id': False, 'name': name,
                                  'work_entry_type_id': attendance.id, 'state': 'validated'})

    def action_refuse(self):
        """
        Override to archive linked work entries and recreate attendance work entries
        where the refused leave was.
        """
        res = super(HrLeave, self).action_refuse()
        # arj fixme necessary ???
        self.flush()
        work_entries = self.env['hr.work.entry'].sudo().search([('leave_id', 'in', self.ids)])

        work_entries.write({'active': False})
        self._refused_work_entry(work_entries)

        return res

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ If an employee is currently working full time but requests a leave next month
            where he has a new contract working only 3 days/week. This should be taken into
            account when computing the number of days for the leave (2 weeks leave = 6 days).
            Override this method to get number of days according to the contract's calendar
            at the time of the leave.
        """
        days = super(HrLeave, self)._get_number_of_days(date_from, date_to, employee_id)
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            calendar = self._get_calendar()
            return employee._get_work_days_data_batch(date_from, date_to, calendar=calendar)[employee.id]

        return days

    def _get_calendar(self):
        self.ensure_one()
        if self.date_from and self.date_to:
            return self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
        return super()._get_calendar()
