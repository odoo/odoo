# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class Project(models.Model):
    _inherit = "project.project"

    allow_timesheets = fields.Boolean("Allow timesheets", default=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", ondelete='set null',
        help="Link this project to an analytic account if you need financial management on projects. "
             "It enables you to connect projects with budgets, planning, cost and revenue analysis, timesheets on projects, etc.")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        domain = []
        if self.partner_id:
            domain = [('partner_id', '=', self.partner_id.id)]
        return {'domain': {'analytic_account_id': domain}}

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account(self):
        if not self.analytic_account_id:
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
            analytic_account = self.env['account.analytic.account'].create({
                'name': values.get('name', _('Unkwon Analytic Account')),
                'company_id': values.get('company_id', self.env.user.company_id.id),
                'partner_id': values.get('partner_id'),
                'active': True,
            })
            values['analytic_account_id'] = analytic_account.id
        return super(Project, self).create(values)

    @api.multi
    def write(self, values):
        result = super(Project, self).write(values)
        # create the AA for project still allowing timesheet
        for project in self:
            if project.allow_timesheets and not project.analytic_account_id:
                project._create_analytic_account()
        return result

    @api.multi
    def unlink(self):
        """ Delete the empty related analytic account """
        analytic_accounts_to_delete = self.env['account.analytic.account']
        for project in self:
            if project.analytic_account_id and not project.analytic_account_id.line_ids:
                analytic_accounts_to_delete |= project.analytic_account_id
        result = super(Project, self).unlink()
        analytic_accounts_to_delete.unlink()
        return result

    @api.model
    def _init_data_analytic_account(self):
        self.search([('analytic_account_id', '=', False), ('allow_timesheets', '=', True)])._create_analytic_account()

    def _create_analytic_account(self):
        for project in self:
            analytic_account = self.env['account.analytic.account'].create({
                'name': project.name,
                'company_id': project.company_id.id,
                'partner_id': project.partner_id.id,
                'active': True,
            })
            project.write({'analytic_account_id': analytic_account.id})


class Task(models.Model):
    _inherit = "project.task"

    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", related='project_id.analytic_account_id', readonly=True)
    allow_timesheets = fields.Boolean("Allow timesheets", compute='_compute_allow_timesheets', help="Timesheets can be logged on this task.")
    remaining_hours = fields.Float("Remaining Hours", compute='_compute_remaining_hours', inverse='_inverse_remaining_hours', help="Total remaining time, can be re-estimated periodically by the assignee of the task.")
    effective_hours = fields.Float("Hours Spent", compute='_compute_effective_hours', compute_sudo=True, store=True, help="Computed using the sum of the task work done.")
    total_hours_spent = fields.Float("Total Hours", compute='_compute_total_hours_spent', store=True, help="Computed as: Time Spent + Sub-tasks Hours.")
    progress = fields.Float("Progress", compute='_compute_progress_hours', store=True, group_operator="avg", help="Display progress of current task.")
    subtask_effective_hours = fields.Float("Sub-tasks Hours Spent", compute='_compute_subtask_effective_hours', store=True, help="Sum of actually spent hours on the subtask(s)", oldname='children_hours')
    timesheet_ids = fields.One2many('account.analytic.line', 'task_id', 'Timesheets')

    @api.depends('project_id.allow_timesheets', 'project_id.analytic_account_id')
    def _compute_allow_timesheets(self):
        for task in self:
            task.allow_timesheets = task.project_id.allow_timesheets and task.project_id.analytic_account_id.active

    @api.depends('timesheet_ids.unit_amount')
    def _compute_effective_hours(self):
        for task in self:
            task.effective_hours = sum(task.timesheet_ids.mapped('unit_amount'))

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

    @api.onchange('remaining_hours')
    def _inverse_remaining_hours(self):
        for task in self:
            task.planned_hours = task.remaining_hours + task.effective_hours + task.subtask_effective_hours

    @api.depends('effective_hours', 'subtask_effective_hours')
    def _compute_total_hours_spent(self):
        for task in self:
            task.total_hours_spent = task.effective_hours + task.subtask_effective_hours

    @api.depends('child_ids.effective_hours', 'child_ids.subtask_effective_hours')
    def _compute_subtask_effective_hours(self):
        for task in self:
            task.subtask_effective_hours = sum(child_task.effective_hours + child_task.subtask_effective_hours for child_task in task.child_ids)

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
