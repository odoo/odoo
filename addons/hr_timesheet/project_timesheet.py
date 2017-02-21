# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class Project(models.Model):
    _inherit = "project.project"

    subtask_project_id = fields.Many2one(
        'project.project', string='Sub-task Project', ondelete="restrict",
        help="Choosing a sub-tasks project will both enable sub-tasks and set their default project (possibly the project itself)")
    allow_timesheets = fields.Boolean("Allow timesheets", default=True)

class Task(models.Model):
    _inherit = "project.task"

    @api.multi
    def _get_subtask_count(self):
        for task in self:
            task.subtask_count = self.search_count([('id', 'child_of', task.id), ('id', '!=', task.id)])

    @api.depends('stage_id', 'timesheet_ids.unit_amount', 'planned_hours', 'child_ids.stage_id',
                 'child_ids.planned_hours', 'child_ids.effective_hours', 'child_ids.children_hours', 'child_ids.timesheet_ids.unit_amount')
    def _hours_get(self):
        for task in self.sorted(key='id', reverse=True):
            for child_task in task.child_ids:
                if child_task.stage_id and not child_task.stage_id.fold:
                    task.children_hours += child_task.effective_hours + child_task.children_hours
                else:
                    task.children_hours += max(child_task.planned_hours, child_task.effective_hours + child_task.children_hours)

            task.effective_hours = sum(task.timesheet_ids.mapped('unit_amount'))
            task.remaining_hours = task.planned_hours - task.effective_hours - task.children_hours
            task.total_hours = max(task.planned_hours, task.effective_hours)
            task.total_hours_spent = task.effective_hours + task.children_hours
            task.delay_hours = max(-task.remaining_hours, 0.0)

            if task.stage_id and task.stage_id.fold:
                task.progress = 100.0
            elif (task.planned_hours > 0.0):
                task.progress = round(100.0 * (task.effective_hours + task.children_hours) / task.planned_hours, 2)
            else:
                task.progress = 0.0

    remaining_hours = fields.Float(compute='_hours_get', store=True, string='Remaining Hours', help="Total remaining time, can be re-estimated periodically by the assignee of the task.")
    effective_hours = fields.Float(compute='_hours_get', store=True, string='Hours Spent', help="Computed using the sum of the task work done.")
    total_hours = fields.Float(compute='_hours_get', store=True, string='Total', help="Computed as: Time Spent + Remaining Time.")
    total_hours_spent = fields.Float(compute='_hours_get', store=True, string='Total Hours', help="Computed as: Time Spent + Sub-tasks Hours.")
    progress = fields.Float(compute='_hours_get', store=True, string='Working Time Recorded', group_operator="avg")
    delay_hours = fields.Float(compute='_hours_get', store=True, string='Delay Hours', help="Computed as difference between planned hours by the project manager and the total hours of the task.")
    children_hours = fields.Float(compute='_hours_get', store=True, string='Sub-tasks Hours', help="Sum of the planned hours of all sub-tasks (when a sub-task is closed or its spent hours exceed its planned hours, spent hours are counted instead)")
    timesheet_ids = fields.One2many('account.analytic.line', 'task_id', 'Timesheets')

    parent_id = fields.Many2one('project.task', string='Parent Task')
    child_ids = fields.One2many('project.task', 'parent_id', string="Sub-tasks")
    subtask_project_id = fields.Many2one('project.project', related="project_id.subtask_project_id", string='Sub-task Project', readonly=True)
    subtask_count = fields.Integer(compute='_get_subtask_count', type='integer', string="Sub-task count")

    _constraints = [(models.BaseModel._check_recursion, 'Circular references are not permitted between tasks and sub-tasks', ['parent_id'])]
