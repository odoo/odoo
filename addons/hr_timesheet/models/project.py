# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class Project(models.Model):
    _inherit = "project.project"

    allow_timesheets = fields.Boolean("Allow timesheets", default=True, help="Enable timesheeting on the project.")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        domain = []
        if self.partner_id:
            domain = [('partner_id', '=', self.partner_id.id)]
        return {'domain': {'analytic_account_id': domain}}

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account(self):
        if not self.analytic_account_id and self._origin:
            self.allow_timesheets = False

    @api.constrains('allow_timesheets', 'analytic_account_id')
    def _check_allow_timesheet(self):
        for project in self:
            if project.allow_timesheets and not project.analytic_account_id:
                raise ValidationError(_('To allow timesheet, your project %s should have an analytic account set.' % (project.name,)))

    @api.model
    def name_create(self, name):
        """ Create a project with name_create should generate analytic account creation """
        values = {
            'name': name,
            'allow_timesheets': True,
        }
        return self.create(values).name_get()[0]

    @api.model
    def create(self, values):
        """ Create an analytic account if project allow timesheet and don't provide one
            Note: create it before calling super() to avoid raising the ValidationError from _check_allow_timesheet
        """
        allow_timesheets = values['allow_timesheets'] if 'allow_timesheets' in values else self.default_get(['allow_timesheets'])['allow_timesheets']
        if allow_timesheets and not values.get('analytic_account_id'):
            analytic_account = self._create_analytic_account_from_values(values)
            values['analytic_account_id'] = analytic_account.id
        return super(Project, self).create(values)

    def write(self, values):
        # create the AA for project still allowing timesheet
        if values.get('allow_timesheets'):
            for project in self:
                if not project.analytic_account_id and not values.get('analytic_account_id'):
                    project._create_analytic_account()
        result = super(Project, self).write(values)
        return result

    # ---------------------------------------------------
    #  Business Methods
    # ---------------------------------------------------

    @api.model
    def _init_data_analytic_account(self):
        self.search([('analytic_account_id', '=', False), ('allow_timesheets', '=', True)])._create_analytic_account()


class Task(models.Model):
    _inherit = "project.task"

    analytic_account_active = fields.Boolean("Analytic Account", related='project_id.analytic_account_id.active', readonly=True)
    allow_timesheets = fields.Boolean("Allow timesheets", related='project_id.allow_timesheets', help="Timesheets can be logged on this task.", readonly=True)
    remaining_hours = fields.Float("Remaining Hours", compute='_compute_remaining_hours', store=True, readonly=True, help="Total remaining time, can be re-estimated periodically by the assignee of the task.")
    effective_hours = fields.Float("Hours Spent", compute='_compute_effective_hours', compute_sudo=True, store=True, help="Computed using the sum of the task work done.")
    total_hours_spent = fields.Float("Total Hours", compute='_compute_total_hours_spent', store=True, help="Computed as: Time Spent + Sub-tasks Hours.")
    progress = fields.Float("Progress", compute='_compute_progress_hours', store=True, group_operator="avg", help="Display progress of current task.")
    subtask_effective_hours = fields.Float("Sub-tasks Hours Spent", compute='_compute_subtask_effective_hours', store=True, help="Sum of actually spent hours on the subtask(s)", oldname='children_hours')
    timesheet_ids = fields.One2many('account.analytic.line', 'task_id', 'Timesheets')

    @api.depends('timesheet_ids.unit_amount')
    def _compute_effective_hours(self):
        for task in self:
            task.effective_hours = round(sum(task.timesheet_ids.mapped('unit_amount')), 2)

    @api.depends('effective_hours', 'subtask_effective_hours', 'planned_hours')
    def _compute_progress_hours(self):
        for task in self:
            if (task.planned_hours > 0.0):
                task_total_hours = task.effective_hours + task.subtask_effective_hours
                if task_total_hours > task.planned_hours:
                    task.progress = 100
                else:
                    task.progress = round(100.0 * task_total_hours / task.planned_hours, 2)
            else:
                task.progress = 0.0

    @api.depends('effective_hours', 'subtask_effective_hours', 'planned_hours')
    def _compute_remaining_hours(self):
        for task in self:
            task.remaining_hours = task.planned_hours - task.effective_hours - task.subtask_effective_hours

    @api.depends('effective_hours', 'subtask_effective_hours')
    def _compute_total_hours_spent(self):
        for task in self:
            task.total_hours_spent = task.effective_hours + task.subtask_effective_hours

    @api.depends('child_ids.effective_hours', 'child_ids.subtask_effective_hours')
    def _compute_subtask_effective_hours(self):
        for task in self:
            task.subtask_effective_hours = sum(child_task.effective_hours + child_task.subtask_effective_hours for child_task in task.child_ids)

    # ---------------------------------------------------------
    # ORM
    # ---------------------------------------------------------

    def write(self, values):
        # a timesheet must have an analytic account (and a project)
        if 'project_id' in values and self and not values.get('project_id'):
                raise UserError(_('This task must be part of a project because there are some timesheets linked to it.'))
        return super(Task, self).write(values)

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Set the correct label for `unit_amount`, depending on company UoM """
        result = super(Task, self)._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        result['arch'] = self.env['account.analytic.line']._apply_timesheet_label(result['arch'])
        return result
