# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from math import ceil
from odoo import api, fields, models
from datetime import datetime


class ProjectTaskCreateTimesheet(models.TransientModel):
    _name = 'project.task.create.timesheet'
    _description = "Create Timesheet from task"

    _sql_constraints = [('time_positive', 'CHECK(time_spent > 0)', 'The timesheet\'s time must be positive' )]

    time_spent = fields.Float('Time', digits=(16, 2))
    description = fields.Char('Description')
    task_id = fields.Many2one(
        'project.task', "Task", required=True,
        default=lambda self: self.env.context.get('active_id', None),
        help="Task for which we are creating a sales order",
    )

    def save_timesheet(self):
        minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('hr_timesheet.timesheet_min_duration', 0))
        rounding = int(self.env['ir.config_parameter'].sudo().get_param('hr_timesheet.timesheet_rounding', 0))
        minutes_spent = max(minimum_duration, self.time_spent * 60)
        if rounding and ceil(minutes_spent % rounding) != 0:
            minutes_spent = ceil(minutes_spent / rounding) * rounding

        values = {
            'task_id': self.task_id.id,
            'project_id': self.task_id.project_id.id,
            'date': fields.Date.context_today(self),
            'name': self.description,
            'user_id': self.env.uid,
            'unit_amount': minutes_spent / 60,
        }
        return self.env['account.analytic.line'].create(values)
