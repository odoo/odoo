# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api


class Task(models.Model):
    _inherit = "project.task"

    def _get_total_hours(self):
        return super(Task, self)._get_total_hours() + self.effective_hours

    @api.depends('timesheet_ids', 'timesheet_ids.unit_amount', 'planned_hours')
    def _hours_get(self):
        for task in self:
            task.effective_hours = sum(task.timesheet_ids.mapped('unit_amount'))
            task.remaining_hours = task.planned_hours - task.effective_hours
            task.total_hours = max(task.planned_hours, task.effective_hours)
            task.delay_hours = max(-task.remaining_hours, 0.0)

            if task.stage_id and task.stage_id.fold:
                task.progress = 100.0
            elif (task.planned_hours > 0.0 and task.effective_hours):
                task.progress = round(min(100.0 * task.effective_hours / task.planned_hours, 99.99), 2)
            else:
                task.progress = 0.0

    remaining_hours = fields.Float(compute='_hours_get', store=True, string='Remaining Hours', help="Total remaining time, can be re-estimated periodically by the assignee of the task.")
    effective_hours = fields.Float(compute='_hours_get', store=True, string='Hours Spent', help="Computed using the sum of the task work done.")
    total_hours = fields.Float(compute='_hours_get', store=True, string='Total', help="Computed as: Time Spent + Remaining Time.")
    progress = fields.Float(compute='_hours_get', store=True, string='Progress (%)', group_operator="avg", help="If the task has a progress of 99.99% you should close the task if it's finished or reevaluate the time", default=0.0)
    delay_hours = fields.Float(compute='_hours_get', store=True, string='Delay Hours', help="Computed as difference between planned hours by the project manager and the total hours of the task.")
    timesheet_ids = fields.One2many('account.analytic.line', 'task_id', 'Timesheets')
