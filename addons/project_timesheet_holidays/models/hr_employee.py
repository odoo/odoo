# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        if self.env.context.get('salary_simulation'):
            return employees

        # We need to create timesheet entries for the global time off that are already created
        # and are planned for after this employee creation date

        # First we look for the global time off that are already planned after today
        today = fields.Datetime.today()
        lines_vals = []
        for employee in employees:
            global_leaves = employee.resource_calendar_id.global_leave_ids.filtered(lambda l: l.date_from >= today)
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
        self.env['account.analytic.line'].sudo().create(lines_vals)
        return employees
