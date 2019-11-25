# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from math import ceil

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class Project(models.Model):
    _inherit = "project.project"

    allow_timesheets = fields.Boolean("Timesheets", default=True, help="Enable timesheeting on the project.")
    analytic_account_id = fields.Many2one(
        # note: replaces ['|', ('company_id', '=', False), ('company_id', '=', company_id)]
        domain="""[
            '|', ('company_id', '=', False), ('company_id', '=', company_id),
            ('partner_id', '=?', partner_id),
        ]"""
    )
    allow_timesheet_timer = fields.Boolean('Timesheet Timer', default=False, help="Use a timer to record timesheets on tasks")

    _sql_constraints = [
        ('timer_only_when_timesheet', "CHECK((allow_timesheets = 'f' AND allow_timesheet_timer = 'f') OR (allow_timesheets = 't'))", 'The timesheet timer can only be activated on project allowing timesheets.'),
    ]

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account(self):
        if not self.analytic_account_id and self._origin:
            self.allow_timesheets = False

    @api.constrains('allow_timesheets', 'analytic_account_id')
    def _check_allow_timesheet(self):
        for project in self:
            if project.allow_timesheets and not project.analytic_account_id:
                raise ValidationError(_('To allow timesheet, your project %s should have an analytic account set.' % (project.name,)))

    @api.onchange('allow_timesheets')
    def _onchange_allow_timesheets(self):
        if not self.allow_timesheets:
            self.allow_timesheet_timer = False

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
        if 'allow_timesheet_timer' in values and not values.get('allow_timesheet_timer'):
            self.with_context(active_test=False).mapped('task_ids').write({
                'timer_start': False,
                'timer_pause': False,
            })
        return result

    @api.model
    def _init_data_analytic_account(self):
        self.search([('analytic_account_id', '=', False), ('allow_timesheets', '=', True)])._create_analytic_account()


class Task(models.Model):
    _name = "project.task"
    _inherit = ["project.task", "timer.mixin"]

    analytic_account_active = fields.Boolean("Analytic Account", related='project_id.analytic_account_id.active', readonly=True)
    allow_timesheets = fields.Boolean("Allow timesheets", related='project_id.allow_timesheets', help="Timesheets can be logged on this task.", readonly=True)
    remaining_hours = fields.Float("Remaining Hours", compute='_compute_remaining_hours', store=True, readonly=True, help="Total remaining time, can be re-estimated periodically by the assignee of the task.")
    effective_hours = fields.Float("Hours Spent", compute='_compute_effective_hours', compute_sudo=True, store=True, help="Computed using the sum of the task work done.")
    total_hours_spent = fields.Float("Total Hours", compute='_compute_total_hours_spent', store=True, help="Computed as: Time Spent + Sub-tasks Hours.")
    progress = fields.Float("Progress", compute='_compute_progress_hours', store=True, group_operator="avg", help="Display progress of current task.")
    subtask_effective_hours = fields.Float("Sub-tasks Hours Spent", compute='_compute_subtask_effective_hours', store=True, help="Sum of actually spent hours on the subtask(s)")
    timesheet_ids = fields.One2many('account.analytic.line', 'task_id', 'Timesheets')

    timer_start = fields.Datetime("Timesheet Timer Start")
    timer_pause = fields.Datetime("Timesheet Timer Last Pause")
    # YTI FIXME: Those field seems quite useless
    timesheet_timer_first_start = fields.Datetime("Timesheet Timer First Use", readonly=True)
    timesheet_timer_last_stop = fields.Datetime("Timesheet Timer Last Use", readonly=True)
    display_timesheet_timer = fields.Boolean("Display Timesheet Time", compute='_compute_display_timesheet_timer')

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

    @api.depends('allow_timesheets', 'project_id.allow_timesheet_timer', 'analytic_account_active')
    def _compute_display_timesheet_timer(self):
        for task in self:
            task.display_timesheet_timer = task.allow_timesheets and task.project_id.allow_timesheet_timer and task.analytic_account_active

    def action_view_subtask_timesheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheets'),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form',
            'domain': [('project_id', '!=', False), ('task_id', 'in', self.child_ids.ids)],
        }

    def write(self, values):
        # a timesheet must have an analytic account (and a project)
        if 'project_id' in values and self and not values.get('project_id'):
            raise UserError(_('This task must be part of a project because there are some timesheets linked to it.'))
        return super(Task, self).write(values)

    def name_get(self):
        if self.env.context.get('hr_timesheet_display_remaining_hours'):
            name_mapping = dict(super().name_get())
            for task in self:
                if task.allow_timesheets and task.planned_hours > 0:
                    hours, mins = (str(int(duration)).rjust(2, '0') for duration in divmod(abs(task.remaining_hours) * 60, 60))
                    hours_left = _("(%s%s:%s remaining)") % ('-' if task.remaining_hours < 0 else '', hours, mins)
                    name_mapping[task.id] = name_mapping.get(task.id, '') + " ‒ " + hours_left
            return list(name_mapping.items())
        return super().name_get()

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Set the correct label for `unit_amount`, depending on company UoM """
        result = super(Task, self)._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        result['arch'] = self.env['account.analytic.line']._apply_timesheet_label(result['arch'])
        return result

    def action_timer_start(self):
        self.ensure_one()
        if not self.timesheet_timer_first_start:
            self.write({'timesheet_timer_first_start': fields.Datetime.now()})
        super(Task, self).action_timer_start()

    def action_timer_stop(self):
        self.ensure_one()
        if self.timer_start:  # timer was either running or paused
            minutes_spent = self._get_minutes_spent()
            minutes_spent = self._timer_rounding(minutes_spent)
            return self._action_create_timesheet(minutes_spent * 60 / 3600)
        return False

    def _timer_rounding(self, minutes_spent):
        minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('hr_timesheet.timesheet_min_duration', 0))
        rounding = int(self.env['ir.config_parameter'].sudo().get_param('hr_timesheet.timesheet_rounding', 0))
        minutes_spent = max(minimum_duration, minutes_spent)
        if rounding and ceil(minutes_spent % rounding) != 0:
            minutes_spent = ceil(minutes_spent / rounding) * rounding
        return minutes_spent

    def _action_create_timesheet(self, time_spent):
        return {
            "name": _("Validate Spent Time"),
            "type": 'ir.actions.act_window',
            "res_model": 'project.task.create.timesheet',
            "views": [[False, "form"]],
            "target": 'new',
            "context": {
                **self.env.context,
                'active_id': self.id,
                'active_model': 'project.task',
                'default_time_spent': time_spent,
            },
        }
