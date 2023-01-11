# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from pytz import timezone, utc

from odoo import api, fields, models, _


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    timesheet_ids = fields.One2many('account.analytic.line', 'global_leave_id', string="Analytic Lines")

    def _get_resource_calendars(self):
        leaves_with_calendar = self.filtered('calendar_id')
        calendars = leaves_with_calendar.calendar_id
        leaves_wo_calendar = self - leaves_with_calendar
        if leaves_wo_calendar:
            calendars += self.env['resource.calendar'].search([('company_id', 'in', leaves_wo_calendar.company_id.ids)])
        return calendars

    def _work_time_per_day(self, resource_calendars=False):
        """ Get work time per day based on the calendar and its attendances

            1) Gets all calendars with their characteristics (i.e.
                (a) the leaves in it,
                (b) the resources which have a leave,
                (c) the oldest and
                (d) the latest leave dates
               ) for leaves in self.
            2) Search the attendances based on the characteristics retrieved for each calendar.
                The attendances found are the ones between the date_from of the oldest leave
                and the date_to of the most recent leave.
            3) Create a dict as result of this method containing:
                {
                    leave: {
                            max(date_start of work hours, date_start of the leave):
                                the duration in days of the work including the leave
                    }
                }
        """
        resource_calendars = resource_calendars or self._get_resource_calendars()
        leaves_read_group = self.env['resource.calendar.leaves']._read_group(
            [('id', 'in', self.ids)],
            ['calendar_id', 'ids:array_agg(id)', 'resource_ids:array_agg(resource_id)', 'min_date_from:min(date_from)', 'max_date_to:max(date_to)'],
            ['calendar_id'],
        )
        # dict of keys: calendar_id
        #   and values : { 'date_from': datetime, 'date_to': datetime, resources: self.env['resource.resource'] }
        cal_attendance_intervals_dict = {}
        for res in leaves_read_group:
            calendar_data = {
                'date_from': utc.localize(res['min_date_from']),
                'date_to': utc.localize(res['max_date_to']),
                'resources': self.env['resource.resource'].browse(res['resource_ids'] if res['resource_ids'] and res['resource_ids'][0] else []),
                'leaves': self.env['resource.calendar.leaves'].browse(res['ids']),
            }
            if not res.get('calendar_id', False):
                for calendar_id in resource_calendars.ids:
                    cal_attendance_intervals_dict[calendar_id] = calendar_data
            else:
                cal_attendance_intervals_dict[res['calendar_id'][0]] = calendar_data
        # to easily find the calendar with its id.
        calendars_dict = {calendar.id: calendar for calendar in resource_calendars}

        # dict of keys: calendar_id
        #   and values: a dict of keys: leave.id
        #         and values: a dict of keys: date
        #              and values: number of days
        results = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        for calendar_id, cal_attendance_intervals_params_entry in cal_attendance_intervals_dict.items():
            calendar = calendars_dict[calendar_id]
            work_hours_intervals = calendar._attendance_intervals_batch(
                cal_attendance_intervals_params_entry['date_from'],
                cal_attendance_intervals_params_entry['date_to'],
                cal_attendance_intervals_params_entry['resources'],
                tz=timezone(calendar.tz)
            )
            for leave in cal_attendance_intervals_params_entry['leaves']:
                work_hours_data = work_hours_intervals[leave.resource_id.id]

                for date_from, date_to, dummy in work_hours_data:
                    if date_to > utc.localize(leave.date_from) and date_from < utc.localize(leave.date_to):
                        tmp_start = max(date_from, utc.localize(leave.date_from))
                        tmp_end = min(date_to, utc.localize(leave.date_to))
                        results[calendar_id][leave.id][tmp_start.date()] += (tmp_end - tmp_start).total_seconds() / 3600
                results[calendar_id][leave.id] = sorted(results[calendar_id][leave.id].items())
        return results

    def _timesheet_create_lines(self):
        """ Create timesheet leaves for each employee using the same calendar containing in self.calendar_id

            If the employee has already a time off in the same day then no timesheet should be created.
        """
        resource_calendars = self._get_resource_calendars()
        work_hours_data = self._work_time_per_day(resource_calendars)
        employees_groups = self.env['hr.employee']._read_group(
            [('resource_calendar_id', 'in', resource_calendars.ids)],
            ['resource_calendar_id', 'ids:array_agg(id)'],
            ['resource_calendar_id'])
        mapped_employee = {
            employee['resource_calendar_id'][0]: self.env['hr.employee'].browse(employee['ids'])
            for employee in employees_groups
        }
        employee_ids_set = set()
        employee_ids_set.update(*[line['ids'] for line in employees_groups])
        min_date = max_date = None
        for values in work_hours_data.values():
            for vals in values.values():
                for d, dummy in vals:
                    if not min_date and not max_date:
                        min_date = max_date = d
                    elif d < min_date:
                        min_date = d
                    elif d > max_date:
                        max_date = d

        holidays_read_group = self.env['hr.leave']._read_group([
            ('employee_id', 'in', list(employee_ids_set)),
            ('date_from', '<=', max_date),
            ('date_to', '>=', min_date),
            ('state', 'not in', ('cancel', 'refuse')),
        ], ['date_from_list:array_agg(date_from)', 'date_to_list:array_agg(date_to)', 'employee_id'], ['employee_id'])
        holidays_by_employee = {
            line['employee_id'][0]: [
                (date_from.date(), date_to.date()) for date_from, date_to in zip(line['date_from_list'], line['date_to_list'])
            ] for line in holidays_read_group
        }
        vals_list = []

        def get_timesheets_data(employees, work_hours_list, vals_list):
            for employee in employees:
                holidays = holidays_by_employee.get(employee.id)
                for index, (day_date, work_hours_count) in enumerate(work_hours_list):
                    if not holidays or all(not (date_from <= day_date and date_to >= day_date) for date_from, date_to in holidays):
                        vals_list.append(
                            leave._timesheet_prepare_line_values(
                                index,
                                employee,
                                work_hours_list,
                                day_date,
                                work_hours_count
                            )
                        )
            return vals_list

        for leave in self:
            if not leave.calendar_id:
                for calendar_id, calendar_employees in mapped_employee.items():
                    work_hours_list = work_hours_data[calendar_id][leave.id]
                    vals_list = get_timesheets_data(calendar_employees, work_hours_list, vals_list)
            else:
                employees = mapped_employee.get(leave.calendar_id.id, self.env['hr.employee'])
                work_hours_list = work_hours_data[leave.calendar_id.id][leave.id]
                vals_list = get_timesheets_data(employees, work_hours_list, vals_list)

        return self.env['account.analytic.line'].sudo().create(vals_list)

    def _timesheet_prepare_line_values(self, index, employee_id, work_hours_data, day_date, work_hours_count):
        self.ensure_one()
        return {
            'name': _("Time Off (%s/%s)", index + 1, len(work_hours_data)),
            'project_id': employee_id.company_id.internal_project_id.id,
            'task_id': employee_id.company_id.leave_timesheet_task_id.id,
            'account_id': employee_id.company_id.internal_project_id.analytic_account_id.id,
            'unit_amount': work_hours_count,
            'user_id': employee_id.user_id.id,
            'date': day_date,
            'global_leave_id': self.id,
            'employee_id': employee_id.id,
            'company_id': employee_id.company_id.id,
        }

    def _generate_timesheeets(self):
        results_with_leave_timesheet = self.filtered(lambda r: not r.resource_id and r.company_id.internal_project_id and r.company_id.leave_timesheet_task_id)
        if results_with_leave_timesheet:
            results_with_leave_timesheet._timesheet_create_lines()

    @api.model_create_multi
    def create(self, vals_list):
        results = super(ResourceCalendarLeaves, self).create(vals_list)
        results._generate_timesheeets()
        return results

    def write(self, vals):
        date_from, date_to, calendar_id = vals.get('date_from'), vals.get('date_to'), vals.get('calendar_id')
        global_time_off_updated = self.env['resource.calendar.leaves']
        if date_from or date_to or 'calendar_id' in vals:
            global_time_off_updated = self.filtered(lambda r: (date_from is not None and r.date_from != date_from) or (date_to is not None and r.date_to != date_to) or (calendar_id is None or r.calendar_id.id != calendar_id))
            timesheets = global_time_off_updated.sudo().timesheet_ids
            if timesheets:
                timesheets.write({'global_leave_id': False})
                timesheets.unlink()
        result = super(ResourceCalendarLeaves, self).write(vals)
        global_time_off_updated and global_time_off_updated.sudo()._generate_timesheeets()
        return result
