# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def create(self, vals):
        employees = super(Employee, self).create(vals)

        # We need to create timesheet entries for the global time off that are already created
        # and are planned for after this employee creation date

        self._create_future_public_holidays_timesheets(employees)
        return employees

    def write(self, vals):
        result = super(Employee, self).write(vals)
        if 'active' in vals or 'resource_calendar_id' in vals:
            has_calendar_future_holidays = 'resource_calendar_id' in vals and \
                self.env['resource.calendar.leaves'].search([
                    ('date_from', '>=', fields.date.today()),
                    ('calendar_id', '=', vals['resource_calendar_id'])
                ], limit=1)
            if not vals.get('active') or has_calendar_future_holidays:
                # Delete future holiday timesheets
                self._delete_future_public_holidays_timesheets(vals)
            if vals.get('active') or has_calendar_future_holidays:
                # Create future holiday timesheets
                self._create_future_public_holidays_timesheets(self)
        return result

    def _delete_future_public_holidays_timesheets(self, vals):
        future_timesheets = self.env['account.analytic.line'].sudo().search([('global_leave_id.calendar_id', '!=', vals.get('resource_calendar_id', False)), ('date', '>=', fields.date.today()), ('employee_id', 'in', self.ids)])
        future_timesheets.write({'global_leave_id': False})
        future_timesheets.unlink()

    def _create_future_public_holidays_timesheets(self, employees):
        lines_vals = []
        for employee in employees:
            if not employee.active:
                continue
            # First we look for the global time off that are already planned after today
            global_leaves = employee.resource_calendar_id.global_leave_ids.filtered(lambda l: l.date_from >= fields.Datetime.today())
            work_hours_data = global_leaves._work_time_per_day()
            for global_time_off in global_leaves:
                for index, (day_date, work_hours_count) in enumerate(work_hours_data[global_time_off.id]):
                    lines_vals.append(
                        global_time_off._timesheet_prepare_line_values(
                            index,
                            employee,
                            work_hours_data[global_time_off.id],
                            day_date,
                            work_hours_count
                        )
                    )
        return self.env['account.analytic.line'].sudo().create(lines_vals)
