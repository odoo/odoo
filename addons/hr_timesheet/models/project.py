# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Project(models.Model):
    _inherit = "project.project"

    allow_timesheets = fields.Boolean("Allow timesheets", default=True)


class Task(models.Model):
    _inherit = "project.task"

    @api.depends('stage_id', 'timesheet_ids.unit_amount', 'planned_hours', 'child_ids.stage_id',
                 'child_ids.planned_hours', 'child_ids.effective_hours', 'child_ids.children_hours', 'child_ids.timesheet_ids.unit_amount')
    def _hours_get(self):
        for task in self.sorted(key='id', reverse=True):
            children_hours = 0
            for child_task in task.child_ids:
                if child_task.stage_id and child_task.stage_id.fold:
                    children_hours += child_task.effective_hours + child_task.children_hours
                else:
                    children_hours += max(child_task.planned_hours, child_task.effective_hours + child_task.children_hours)

            task.children_hours = children_hours
            task.effective_hours = sum(task.sudo().timesheet_ids.mapped('unit_amount'))  # use 'sudo' here to allow project user (without timesheet user right) to create task
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
    progress = fields.Float(compute='_hours_get', store=True, string='Progress', group_operator="avg")
    delay_hours = fields.Float(compute='_hours_get', store=True, string='Delay Hours', help="Computed as difference between planned hours by the project manager and the total hours of the task.")
    children_hours = fields.Float(compute='_hours_get', store=True, string='Sub-tasks Hours', help="Sum of the planned hours of all sub-tasks (when a sub-task is closed or its spent hours exceed its planned hours, spent hours are counted instead)")
    timesheet_ids = fields.One2many('account.analytic.line', 'task_id', 'Timesheets')

    _constraints = [(models.BaseModel._check_recursion, 'Circular references are not permitted between tasks and sub-tasks', ['parent_id'])]


    @api.model
    def create(self, vals):
        context = dict(self.env.context)
        # Remove default_parent_id to avoid a confusion in get_record_data
        if context.get('default_parent_id', False):
            vals['parent_id'] = context.pop('default_parent_id', None)
        task = super(Task, self.with_context(context)).create(vals)
        return task

    @api.multi
    def write(self, values):
        result = super(Task, self).write(values)
        # reassign project_id on related timesheet lines
        if 'project_id' in values:
            project_id = values.get('project_id')
            # a timesheet must have an analytic account (and a project)
            if self and not project_id:
                raise UserError(_('This task must have a project since they are linked to timesheets.'))
            self.sudo().mapped('timesheet_ids').write({
                'project_id': project_id,
                'account_id': self.env['project.project'].browse(project_id).sudo().analytic_account_id.id
            })
        return result