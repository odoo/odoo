# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from pytz import timezone, utc

from odoo import api, fields, models, _


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    timesheet_ids = fields.One2many('account.analytic.line', 'global_leave_id', string="Analytic Lines")

    def _work_time_per_day(self):
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
        leaves_aggregate = self.env['resource.calendar.leaves']._aggregate(
            [('id', 'in', self.ids)],
            ['id:array_agg', 'resource_id:array_agg', 'date_from:min', 'date_to:max'],
            ['calendar_id'],
        )
        # dict of keys: leave.id
        #   and values: a dict of keys: date
        #                   and values: number of days
        results = defaultdict(lambda: defaultdict(float))
        for [calendar], [leaves, resources, min_date_from, max_date_to] in leaves_aggregate.items(as_records=True):
            work_hours_intervals = calendar._attendance_intervals_batch(
                utc.localize(min_date_from),
                utc.localize(max_date_to),
                resources,
                tz=timezone(calendar.tz)
            )
            for leave in leaves:
                work_hours_data = work_hours_intervals[leave.resource_id.id]

                for date_from, date_to, dummy in work_hours_data:
                    if date_to > utc.localize(leave.date_from) and date_from < utc.localize(leave.date_to):
                        tmp_start = max(date_from, utc.localize(leave.date_from))
                        tmp_end = min(date_to, utc.localize(leave.date_to))
                        results[leave.id][tmp_start.date()] += (tmp_end - tmp_start).total_seconds() / 3600
                results[leave.id] = sorted(results[leave.id].items())
        return results

    def _timesheet_create_lines(self):
        """ Create timesheet leaves for each employee using the same calendar containing in self.calendar_id

            If the employee has already a time off in the same day then no timesheet should be created.
        """
        work_hours_data = self._work_time_per_day()
        employees_groups = self.env['hr.employee']._aggregate(
            [('resource_calendar_id', 'in', self.calendar_id.ids)],
            ['id:array_agg'],
            ['resource_calendar_id'])

        employee_ids = [_id for [ids] in employees_groups.values() for _id in ids]
        min_date = max_date = None
        for values in work_hours_data.values():
            for d, dummy in values:
                if not min_date and not max_date:
                    min_date = max_date = d
                elif d < min_date:
                    min_date = d
                elif d > max_date:
                    max_date = d

        holidays_aggregate = self.env['hr.leave']._aggregate([
            ('employee_id', 'in', employee_ids),
            ('date_from', '<=', max_date),
            ('date_to', '>=', min_date),
            ('state', 'not in', ('cancel', 'refuse')),
        ], ['date_from:array_agg', 'date_to:array_agg'], ['employee_id'])
        holidays_by_employee = {
            employee_id: [
                (date_from.date(), date_to.date()) for date_from, date_to in zip(date_from_list, date_to_list)
            ] for [employee_id], [date_from_list, date_to_list] in holidays_aggregate.items()
        }
        vals_list = []
        for leave in self:
            for employee in employees_groups.get_agg(leave.calendar_id, 'id:array_agg', as_record=True):
                holidays = holidays_by_employee.get(employee.id)
                work_hours_list = work_hours_data[leave.id]
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

    @api.model_create_multi
    def create(self, vals_list):
        results = super(ResourceCalendarLeaves, self).create(vals_list)
        results_with_leave_timesheet = results.filtered(lambda r: not r.resource_id.id and r.calendar_id.company_id.internal_project_id and r.calendar_id.company_id.leave_timesheet_task_id)
        results_with_leave_timesheet and results_with_leave_timesheet._timesheet_create_lines()
        return results

    def write(self, vals):
        date_from, date_to, calendar_id = vals.get('date_from'), vals.get('date_to'), vals.get('calendar_id')
        global_time_off_updated = self.env['resource.calendar.leaves']
        if date_from or date_to or 'calendar_id' in vals:
            global_time_off_updated = self.filtered(lambda r: (date_from is not None and r.date_from != date_from) or (date_to is not None and r.date_to != date_to) or (calendar_id is not None and r.calendar_id.id != calendar_id))
            timesheets = global_time_off_updated.sudo().timesheet_ids
            if timesheets:
                timesheets.write({'global_leave_id': False})
                timesheets.unlink()
        result = super(ResourceCalendarLeaves, self).write(vals)
        if global_time_off_updated:
            global_time_offs_with_leave_timesheet = global_time_off_updated.filtered(lambda r: not r.resource_id and r.calendar_id.company_id.internal_project_id and r.calendar_id.company_id.leave_timesheet_task_id)
            global_time_offs_with_leave_timesheet.sudo()._timesheet_create_lines()
        return result
