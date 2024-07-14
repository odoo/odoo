# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, datetime
from typing import Dict, List
import pytz

from odoo import Command, fields, models, api, _
from odoo.osv import expression
from odoo.tools import get_lang
from odoo.addons.project.models.project_task import CLOSED_STATES

class Task(models.Model):
    _inherit = "project.task"

    @api.model
    def default_get(self, fields_list):
        result = super(Task, self).default_get(fields_list)
        is_fsm_mode = self._context.get('fsm_mode')
        if 'project_id' in fields_list and not result.get('project_id') and is_fsm_mode and not (result.get('parent_id') or self._context.get('default_parent_id')):
            company_id = self.env.context.get('default_company_id') or self.env.company.id
            fsm_project = self.env['project.project'].search([('is_fsm', '=', True), ('company_id', '=', company_id)], order='sequence', limit=1)
            if fsm_project:
                result['stage_id'] = self.stage_find(fsm_project.id, [('fold', '=', False)])
                result['project_id'] = fsm_project.id
                result['company_id'] = company_id
        return result

    is_fsm = fields.Boolean(related='project_id.is_fsm', search='_search_is_fsm')
    fsm_done = fields.Boolean("Task Done", compute='_compute_fsm_done', readonly=False, store=True, copy=False)
    # Use to count conditions between : time, worksheet and materials
    # If 2 over 3 are enabled for the project, the required count = 2
    # If 1 over 3 is met (enabled + encoded), the satisfied count = 2
    display_enabled_conditions_count = fields.Integer(compute='_compute_display_conditions_count')
    display_satisfied_conditions_count = fields.Integer(compute='_compute_display_conditions_count')
    display_mark_as_done_primary = fields.Boolean(compute='_compute_mark_as_done_buttons')
    display_mark_as_done_secondary = fields.Boolean(compute='_compute_mark_as_done_buttons')
    partner_phone = fields.Char(
        compute='_compute_partner_phone', inverse='_inverse_partner_phone',
        string="Phone", readonly=False, store=True, copy=False)
    partner_city = fields.Char(related='partner_id.city', readonly=False)
    is_task_phone_update = fields.Boolean(compute='_compute_is_task_phone_update')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {'is_fsm',
                                              'planned_date_begin',
                                              'fsm_done',
                                              'partner_phone',
                                              'partner_city',}

    @api.depends(
        'fsm_done', 'is_fsm', 'timer_start',
        'display_enabled_conditions_count', 'display_satisfied_conditions_count')
    def _compute_mark_as_done_buttons(self):
        for task in self:
            primary, secondary = True, True
            if task.fsm_done or not task.is_fsm or task.timer_start:
                primary, secondary = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    secondary = False
                else:
                    primary = False
            task.update({
                'display_mark_as_done_primary': primary,
                'display_mark_as_done_secondary': secondary,
            })

    @api.depends('partner_id.phone')
    def _compute_partner_phone(self):
        for task in self:
            if task.partner_phone != task.partner_id.phone:
                task.partner_phone = task.partner_id.phone

    def _inverse_partner_phone(self):
        for task in self:
            if task.partner_id and task.partner_phone != task.partner_id.phone:
                task.partner_id.phone = task.partner_phone

    @api.depends('partner_phone', 'partner_id.phone')
    def _compute_is_task_phone_update(self):
        for task in self:
            task.is_task_phone_update = task.partner_phone != task.partner_id.phone

    @api.depends('project_id.allow_timesheets', 'total_hours_spent')
    def _compute_display_conditions_count(self):
        for task in self:
            enabled = 1 if task.project_id.allow_timesheets else 0
            satisfied = 1 if enabled and task.total_hours_spent else 0
            task.update({
                'display_enabled_conditions_count': enabled,
                'display_satisfied_conditions_count': satisfied
            })

    @api.depends('fsm_done', 'display_timesheet_timer', 'timer_start', 'total_hours_spent')
    def _compute_display_timer_buttons(self):
        fsm_done_tasks = self.filtered(lambda task: task.fsm_done)
        fsm_done_tasks.update({
            'display_timer_start_primary': False,
            'display_timer_start_secondary': False,
            'display_timer_stop': False,
            'display_timer_pause': False,
            'display_timer_resume': False,
        })
        super(Task, self - fsm_done_tasks)._compute_display_timer_buttons()

    @api.model
    def _search_is_fsm(self, operator, value):
        query = """
            SELECT p.id
            FROM project_project P
            WHERE P.active = 't' AND P.is_fsm
        """
        operator_new = operator == "=" and "inselect" or "not inselect"
        return [('project_id', operator_new, (query, ()))]

    # TODO: remove in master
    def _onchange_planned_date(self):
        return

    @api.onchange('date_deadline', 'planned_date_begin')
    def _onchange_planned_dates(self):
        if not self.is_fsm:
            return super()._onchange_planned_dates()

    def write(self, vals):
        self_fsm = self.filtered('is_fsm')
        super(Task, self - self_fsm).write(vals.copy())

        is_start_date_set = bool(vals.get('planned_date_begin', False))
        is_end_date_set = bool(vals.get("date_deadline", False))
        both_dates_changed = 'planned_date_begin' in vals and 'date_deadline' in vals
        self_fsm = self_fsm.with_context(fsm_mode=True)

        if self_fsm and (
            (both_dates_changed and is_start_date_set != is_end_date_set) or (not both_dates_changed and (
                ('planned_date_begin' in vals and not all(bool(t.date_deadline) == is_start_date_set for t in self)) or \
                ('date_deadline' in vals and not all(bool(t.planned_date_begin) == is_end_date_set for t in self))
            ))
        ):
            vals.update({"date_deadline": False, "planned_date_begin": False})

        return super(Task, self_fsm).write(vals)

    @api.model
    def _group_expand_project_ids(self, projects, domain, order):
        res = super()._group_expand_project_ids(projects, domain, order)
        if self._context.get('fsm_mode'):
            search_on_comodel = self._search_on_comodel(domain, "project_id", "project.project", order, [('is_fsm', '=', True)])
            res &= search_on_comodel
        return res

    @api.model
    def _group_expand_user_ids(self, users, domain, order):
        res = super()._group_expand_user_ids(users, domain, order)
        if self.env.context.get('fsm_mode'):
            recently_created_tasks_user_ids = self.env['project.task']._read_group([
                ('create_date', '>', datetime.now() - timedelta(days=30)),
                ('is_fsm', '=', True),
                ('user_ids', '!=', False)
            ], [], ['user_ids:array_agg'])[0][0]
            search_domain = ['&', ('company_id', 'in', self.env.companies.ids), '|', '|', ('id', 'in', users.ids), ('groups_id', 'in', self.env.ref('industry_fsm.group_fsm_user').id), ('id', 'in', recently_created_tasks_user_ids)]
            res |= users.search(search_domain, order=order)
        return res

    def _compute_fsm_done(self):
        closed_tasks = self.filtered(lambda t: t.state in CLOSED_STATES)
        closed_tasks.fsm_done = True

    def action_timer_start(self):
        if not self.user_timer_id.timer_start and self.display_timesheet_timer:
            super(Task, self).action_timer_start()
            if self.is_fsm:
                time = fields.Datetime.context_timestamp(self, self.timer_start)
                self.message_post(
                    body=_(
                        'Timer started at: %(date)s %(time)s',
                        date=time.strftime(get_lang(self.env).date_format),
                        time=time.strftime(get_lang(self.env).time_format),
                    ),
                )

    def action_view_timesheets(self):
        kanban_view = self.env.ref('hr_timesheet.view_kanban_account_analytic_line')
        form_view = self.env.ref('industry_fsm.timesheet_view_form')
        tree_view = self.env.ref('industry_fsm.timesheet_view_tree_user_inherit')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Time'),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form,kanban',
            'views': [(tree_view.id, 'list'), (kanban_view.id, 'kanban'), (form_view.id, 'form')],
            'domain': [('task_id', '=', self.id), ('project_id', '!=', False)],
            'context': {
                'fsm_mode': True,
                'default_project_id': self.project_id.id,
                'default_task_id': self.id,
            }
        }

    def action_fsm_validate(self, stop_running_timers=False):
        """ Moves Task to done state.
            If allow billable on task, timesheet product set on project and user has privileges :
            Create SO confirmed with time and material.
        """
        Timer = self.env['timer.timer']
        tasks_running_timer_ids = Timer.search([('res_model', '=', 'project.task'), ('res_id', 'in', self.ids)])
        timesheets = self.env['account.analytic.line'].sudo().search([('task_id', 'in', self.ids)])
        timesheets_running_timer_ids = None
        if timesheets:
            timesheets_running_timer_ids = Timer.search([
                ('res_model', '=', 'account.analytic.line'),
                ('res_id', 'in', timesheets.ids)])
        if tasks_running_timer_ids or timesheets_running_timer_ids:
            if stop_running_timers:
                self._stop_all_timers_and_create_timesheets(tasks_running_timer_ids, timesheets_running_timer_ids, timesheets)
            else:
                wizard = self.env['project.task.stop.timers.wizard'].create({
                    'line_ids': [Command.create({'task_id': task.id}) for task in self],
                })
                return {
                    'name': _('Do you want to stop the running timers?'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'view_id': self.env.ref('industry_fsm.view_task_stop_timer_wizard_form').id,
                    'target': 'new',
                    'res_model': 'project.task.stop.timers.wizard',
                    'res_id': wizard.id,
                }

        self.write({'fsm_done': True, 'state': '1_done'})

        return True

    @api.model
    def _stop_all_timers_and_create_timesheets(self, tasks_running_timer_ids, timesheets_running_timer_ids, timesheets):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        Timesheet = self.env['account.analytic.line']

        if not tasks_running_timer_ids and not timesheets_running_timer_ids:
            return Timesheet

        result = Timesheet
        minimum_duration = int(ConfigParameter.get_param('timesheet_grid.timesheet_min_duration', 0))
        rounding = int(ConfigParameter.get_param('timesheet_grid.timesheet_rounding', 0))
        if tasks_running_timer_ids:
            task_dict = {task.id: task for task in self}
            timesheets_vals = []
            for timer in tasks_running_timer_ids:
                minutes_spent = timer._get_minutes_spent()
                time_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding) / 60
                task = task_dict[timer.res_id]
                timesheets_vals.append({
                    'task_id': task.id,
                    'project_id': task.project_id.id,
                    'user_id': timer.user_id.id,
                    'unit_amount': time_spent,
                })
            tasks_running_timer_ids.sudo().unlink()
            result += Timesheet.sudo().create(timesheets_vals)

        if timesheets_running_timer_ids:
            timesheets_dict = {timesheet.id: timesheet for timesheet in timesheets}
            for timer in timesheets_running_timer_ids:
                timesheet = timesheets_dict[timer.res_id]
                minutes_spent = timer._get_minutes_spent()
                timesheet._add_timesheet_time(minutes_spent)
                result += timesheet
            timesheets_running_timer_ids.sudo().unlink()

        return result

    def action_fsm_navigate(self):
        if not self.partner_id.city or not self.partner_id.country_id:
            return {
                'name': _('Customer'),
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'res_id': self.partner_id.id,
                'view_mode': 'form',
                'view_id': self.env.ref('industry_fsm.view_partner_address_form_industry_fsm').id,
                'target': 'new',
            }
        return self.partner_id.action_partner_navigate()

    def web_read(self, specification: Dict[str, Dict]) -> List[Dict]:
        if len(self) == 1 and 'partner_id' in specification and 'show_address_if_fsm' in specification['partner_id'].get('context', {}):
            specification['partner_id']['context']['show_address'] = self.is_fsm
        return super().web_read(specification)

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def _get_projects_to_make_billable_domain(self, additional_domain=None):
        return expression.AND([
            super()._get_projects_to_make_billable_domain(additional_domain),
            [('is_fsm', '=', False)],
        ])
