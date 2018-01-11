# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class Project(models.Model):
    _inherit = "project.project"

    allow_timesheets = fields.Boolean("Allow timesheets", default=True)


class Task(models.Model):
    _inherit = "project.task"

    remaining_hours = fields.Float("Remaining Hours", compute='_compute_progress_hours', store=True, help="Total remaining time, can be re-estimated periodically by the assignee of the task.")
    effective_hours = fields.Float("Hours Spent", compute='_compute_effective_hours', compute_sudo=True, store=True, help="Computed using the sum of the task work done.")
    total_hours_spent = fields.Float("Total Hours", compute='_compute_progress_hours', store=True, help="Computed as: Time Spent + Sub-tasks Hours.")
    progress = fields.Float("Progress", compute='_compute_progress_hours', store=True, group_operator="avg", help="Display progress of current task. In case if the total spent hours exceeds planned hours then the progress bar may go above 100%")
    subtask_effective_hours = fields.Float("Sub-tasks Hours Spent", compute='_compute_subtask_effective_hours', store=True, help="Sum of actually spent hours on the subtask(s)", oldname='children_hours')
    timesheet_ids = fields.One2many('account.analytic.line', 'task_id', 'Timesheets')

    @api.depends('timesheet_ids.unit_amount')
    def _compute_effective_hours(self):
        for task in self:
            task.effective_hours = sum(task.timesheet_ids.mapped('unit_amount'))

    @api.depends('effective_hours', 'subtask_effective_hours', 'planned_hours')
    def _compute_progress_hours(self):
        for task in self:
            if (task.planned_hours > 0.0):
                task.progress = round(100.0 * (task.effective_hours + task.subtask_effective_hours) / task.planned_hours, 2)
            else:
                task.progress = 0.0

            task.remaining_hours = task.planned_hours - task.effective_hours - task.subtask_effective_hours
            task.total_hours_spent = task.effective_hours + task.subtask_effective_hours

    @api.depends('child_ids.effective_hours', 'child_ids.subtask_effective_hours')
    def _compute_subtask_effective_hours(self):
        for task in self:
            task.subtask_effective_hours = sum(child_task.effective_hours + child_task.subtask_effective_hours for child_task in task.child_ids)
