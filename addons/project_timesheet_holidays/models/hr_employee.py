# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from collections import defaultdict


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        if self.env.context.get('salary_simulation'):
            return employees

        # We need to create timesheet entries for the global time off that are already created
        # and are planned for after this employee creation date
        self.with_context(allowed_company_ids=employees.company_id.ids) \
            ._create_future_public_holidays_timesheets(employees)
        return employees

    def write(self, vals):
        if vals.get('active'):
            inactive_emp = self.filtered(lambda e: not e.active)
        result = super(Employee, self).write(vals)
        self_company = self.with_context(allowed_company_ids=self.company_id.ids)
        if 'active' in vals:
            if vals.get('active'):
                # Create future holiday timesheets
                inactive_emp = inactive_emp.with_env(self_company.env)
                inactive_emp._create_future_public_holidays_timesheets(inactive_emp)
            else:
                # Delete future holiday timesheets
                self_company._delete_future_public_holidays_timesheets()
        elif 'resource_calendar_id' in vals:
            # Update future holiday timesheets
            self_company._delete_future_public_holidays_timesheets()
            self_company._create_future_public_holidays_timesheets(self_company)
        return result

    def _delete_future_public_holidays_timesheets(self):
        future_timesheets = self.env['account.analytic.line'].sudo().search([('global_leave_id', '!=', False), ('date', '>=', fields.date.today()), ('employee_id', 'in', self.ids)])
        future_timesheets.write({'global_leave_id': False})
        future_timesheets.unlink()

    def _create_future_public_holidays_timesheets(self, employees):
        lines_vals = []
        today = fields.Datetime.today()
        global_leaves_wo_calendar = defaultdict(lambda: self.env["resource.calendar.leaves"])
        global_leaves_wo_calendar.update(dict(self.env['resource.calendar.leaves']._read_group(
            [('calendar_id', '=', False), ('date_from', '>=', today)],
            groupby=['company_id'],
            aggregates=['id:recordset'],
        )))
        for employee in employees:
            if not employee.active:
                continue
            # First we look for the global time off that are already planned after today
            global_leaves = employee.resource_calendar_id.global_leave_ids.filtered(lambda l: l.date_from >= today) + global_leaves_wo_calendar[employee.company_id]
            work_hours_data = global_leaves._work_time_per_day()
            for global_time_off in global_leaves:
                for index, (day_date, work_hours_count) in enumerate(work_hours_data[employee.resource_calendar_id.id][global_time_off.id]):
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
