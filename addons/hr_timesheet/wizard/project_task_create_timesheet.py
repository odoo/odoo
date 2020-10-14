# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        values = {
            'task_id': self.task_id.id,
            'project_id': self.task_id.project_id.id,
            'date': fields.Date.context_today(self),
            'name': self.description,
            'user_id': self.env.uid,
            'unit_amount': self.time_spent,
        }
        self.task_id.user_timer_id.unlink()
        return self.env['account.analytic.line'].create(values)
