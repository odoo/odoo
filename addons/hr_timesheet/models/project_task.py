# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import SQL
from odoo.addons.rating.models.rating_data import OPERATOR_MAPPING


PROJECT_TASK_READABLE_FIELDS = {
    'allow_timesheets',
    'analytic_account_active',
    'analytic_account_id',  # To compute `analytic_account_active`
    'effective_hours',
    'encode_uom_in_days',
    'allocated_hours',
    'progress',
    'overtime',
    'remaining_hours',
    'subtask_effective_hours',
    'subtask_allocated_hours',
    'timesheet_ids',
    'total_hours_spent',
}

class Task(models.Model):
    _name = "project.task"
    _inherit = "project.task"

    project_id = fields.Many2one(domain="['|', ('company_id', '=', False), ('company_id', '=?',  company_id), ('is_internal_project', '=', False)]")
    analytic_account_active = fields.Boolean("Active Analytic Account", compute='_compute_analytic_account_active', compute_sudo=True, recursive=True, export_string_translation=False)
    allow_timesheets = fields.Boolean(
        "Allow timesheets",
        compute='_compute_allow_timesheets', search='_search_allow_timesheets',
        compute_sudo=True, readonly=True, export_string_translation=False)
    remaining_hours = fields.Float("Time Remaining", compute='_compute_remaining_hours', store=True, readonly=True, help="Number of allocated hours minus the number of hours spent.")
    remaining_hours_percentage = fields.Float(compute='_compute_remaining_hours_percentage', search='_search_remaining_hours_percentage', export_string_translation=False)
    effective_hours = fields.Float("Time Spent", compute='_compute_effective_hours', compute_sudo=True, store=True)
    total_hours_spent = fields.Float("Total Time Spent", compute='_compute_total_hours_spent', store=True, help="Time spent on this task and its sub-tasks (and their own sub-tasks).")
    progress = fields.Float("Progress", compute='_compute_progress_hours', store=True, aggregator="avg", export_string_translation=False)
    overtime = fields.Float(compute='_compute_progress_hours', store=True)
    subtask_effective_hours = fields.Float("Time Spent on Sub-tasks", compute='_compute_subtask_effective_hours', recursive=True, store=True, help="Time spent on the sub-tasks (and their own sub-tasks) of this task.")
    timesheet_ids = fields.One2many('account.analytic.line', 'task_id', 'Timesheets', export_string_translation=False)
    encode_uom_in_days = fields.Boolean(compute='_compute_encode_uom_in_days', default=lambda self: self._uom_in_days(), export_string_translation=False)
    display_name = fields.Char(help="""Use these keywords in the title to set new tasks:\n
        30h Allocate 30 hours to the task
        #tags Set tags on the task
        @user Assign the task to a user
        ! Set the task a high priority\n
        Make sure to use the right format and order e.g. Improve the configuration screen 5h #feature #v16 @Mitchell !""",
    )
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | PROJECT_TASK_READABLE_FIELDS

    @api.constrains('project_id')
    def _check_project_root(self):
        private_tasks = self.filtered(lambda t: not t.project_id)
        if private_tasks and self.env['account.analytic.line'].sudo().search_count([('task_id', 'in', private_tasks.ids)], limit=1):
            raise UserError(_("This task cannot be private because there are some timesheets linked to it."))

    def _uom_in_days(self):
        return self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day')

    def _compute_encode_uom_in_days(self):
        self.encode_uom_in_days = self._uom_in_days()

    @api.depends('project_id.allow_timesheets')
    def _compute_allow_timesheets(self):
        for task in self:
            task.allow_timesheets = task.project_id.allow_timesheets

    def _search_allow_timesheets(self, operator, value):
        query = self.env['project.project'].sudo()._search([
            ('allow_timesheets', operator, value),
        ])
        return [('project_id', 'in', query)]

    @api.depends('analytic_account_id.active', 'project_id.analytic_account_id.active')
    def _compute_analytic_account_active(self):
        """ Overridden in sale_timesheet """
        for task in self:
            task.analytic_account_active = task._get_task_analytic_account_id().active

    @api.depends('timesheet_ids.unit_amount')
    def _compute_effective_hours(self):
        if not any(self._ids):
            for task in self:
                task.effective_hours = sum(task.timesheet_ids.mapped('unit_amount'))
            return
        timesheet_read_group = self.env['account.analytic.line']._read_group([('task_id', 'in', self.ids)], ['task_id'], ['unit_amount:sum'])
        timesheets_per_task = {task.id: amount for task, amount in timesheet_read_group}
        for task in self:
            task.effective_hours = timesheets_per_task.get(task.id, 0.0)

    @api.depends('effective_hours', 'subtask_effective_hours', 'allocated_hours')
    def _compute_progress_hours(self):
        for task in self:
            if (task.allocated_hours > 0.0):
                task_total_hours = task.effective_hours + task.subtask_effective_hours
                task.overtime = max(task_total_hours - task.allocated_hours, 0)
                task.progress = round(task_total_hours / task.allocated_hours, 2)
            else:
                task.progress = 0.0
                task.overtime = 0

    @api.depends('allocated_hours', 'remaining_hours')
    def _compute_remaining_hours_percentage(self):
        for task in self:
            if task.allocated_hours > 0.0:
                task.remaining_hours_percentage = task.remaining_hours / task.allocated_hours
            else:
                task.remaining_hours_percentage = 0.0

    def _search_remaining_hours_percentage(self, operator, value):
        if operator not in OPERATOR_MAPPING:
            raise NotImplementedError(_('This operator %s is not supported in this search method.', operator))
        sql = SQL("""(
            SELECT id
              FROM %s
             WHERE remaining_hours > 0
               AND allocated_hours > 0
               AND remaining_hours / allocated_hours %s %s
        )""", SQL.identifier(self._table), SQL(operator), value)
        return [('id', 'in', sql)]

    @api.depends('effective_hours', 'subtask_effective_hours', 'allocated_hours')
    def _compute_remaining_hours(self):
        for task in self:
            if not task.allocated_hours:
                task.remaining_hours = 0.0
            else:
                task.remaining_hours = task.allocated_hours - task.effective_hours - task.subtask_effective_hours

    @api.depends('effective_hours', 'subtask_effective_hours')
    def _compute_total_hours_spent(self):
        for task in self:
            task.total_hours_spent = task.effective_hours + task.subtask_effective_hours

    @api.depends('child_ids.effective_hours', 'child_ids.subtask_effective_hours')
    def _compute_subtask_effective_hours(self):
        for task in self.with_context(active_test=False):
            task.subtask_effective_hours = sum(child_task.effective_hours + child_task.subtask_effective_hours for child_task in task.child_ids)

    def _get_group_pattern(self):
        return {
            **super()._get_group_pattern(),
            'allocated_hours': r'\s(\d+(?:\.\d+)?)[hH]',
        }

    def _prepare_pattern_groups(self):
        return [self._get_group_pattern()['allocated_hours']] + super()._prepare_pattern_groups()

    def _get_cannot_start_with_patterns(self):
        return super()._get_cannot_start_with_patterns() + [r'(?!\d+(?:\.\d+)?(?:h|H))']

    def _extract_allocated_hours(self):
        allocated_hours_group = self._get_group_pattern()['allocated_hours']
        if self.allow_timesheets:
            self.allocated_hours = sum(float(num) for num in re.findall(allocated_hours_group, self.display_name))
            self.display_name, dummy = re.subn(allocated_hours_group, '', self.display_name)

    def _get_groups(self):
        return [lambda task: task._extract_allocated_hours()] + super()._get_groups()

    def action_view_subtask_timesheet(self):
        self.ensure_one()
        is_internal_user = self.env.user.has_group('base.group_user')
        task_ids = self.with_context(active_test=False)._get_subtask_ids_per_task_id().get(self.id, [])
        action = self.env["ir.actions.actions"]._for_xml_id("hr_timesheet.timesheet_action_all")
        graph_view_id = self.env.ref("hr_timesheet.view_hr_timesheet_line_graph_by_employee").id
        new_views = []
        for view in action['views']:
            if not is_internal_user:
                if view[1] == 'tree':
                    tree_view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_timesheet.hr_timesheet_line_portal_tree')
                    if tree_view_id:
                        new_views.insert(0, (tree_view_id, 'tree'))
                        continue
                elif view[1] == 'form':
                    form_view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_timesheet.timesheet_view_form_portal_user')
                    if form_view_id:
                        new_views.append((form_view_id, 'form'))
                        continue
                elif view[1] == 'kanban':
                    kanban_view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_timesheet.view_kanban_account_analytic_line_portal_user')
                    if kanban_view_id:
                        new_views.append((kanban_view_id, 'kanban'))
                        continue
            if view[1] == 'graph':
                view = (graph_view_id, 'graph')
            new_views.insert(0, view) if view[1] == 'tree' else new_views.append(view)

        action.update({
            'display_name': _('Timesheets'),
            'context': {'default_project_id': self.project_id.id},
            'domain': [('project_id', '!=', False), ('task_id', 'in', task_ids)],
            'views': new_views,
        })
        return action

    def _get_timesheet(self):
        # Is override in sale_timesheet
        return self.timesheet_ids

    def _get_timesheet_report_data(self):
        subtasks = self._get_all_subtasks()
        timesheets_read_group = self.env['account.analytic.line']._read_group(
            [('task_id', 'in', (self | subtasks).ids)],
            ['task_id'],
            ['id:recordset'],
        )
        timesheets_per_task = dict(timesheets_read_group)
        subtask_ids_per_task_id = defaultdict(list)
        for subtask in subtasks:
            subtask_ids_per_task_id[subtask.parent_id.id].append(subtask.id)
        return {
            'subtask_ids_per_task_id': subtask_ids_per_task_id,
            'timesheets_per_task': timesheets_per_task,
        }

    @api.depends_context('hr_timesheet_display_remaining_hours')
    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('hr_timesheet_display_remaining_hours'):
            for task in self:
                if task.allow_timesheets and task.allocated_hours > 0 and task.encode_uom_in_days:
                    days_left = _("(%s days remaining)", task._convert_hours_to_days(task.remaining_hours))
                    task.display_name = task.display_name + "\u00A0" + days_left
                elif task.allow_timesheets and task.allocated_hours > 0:
                    hours, mins = (str(int(duration)).rjust(2, '0') for duration in divmod(abs(task.remaining_hours) * 60, 60))
                    hours_left = _(
                        "(%(sign)s%(hours)s:%(minutes)s remaining)",
                        sign='-' if task.remaining_hours < 0 else '',
                        hours=hours,
                        minutes=mins,
                    )
                    task.display_name = task.display_name + "\u00A0" + hours_left

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        arch = self.env['account.analytic.line'].sudo()._apply_timesheet_label(arch)
        return arch, view

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_entries(self):
        """
        If some tasks to unlink have some timesheets entries, these
        timesheets entries must be unlinked first.
        In this case, a warning message is displayed through a RedirectWarning
        and allows the user to see timesheets entries to unlink.
        """
        timesheet_data = self.env['account.analytic.line'].sudo()._read_group(
            [('task_id', 'in', self.ids)],
            ['task_id'],
        )
        task_with_timesheets_ids = [task.id for task, in timesheet_data]
        if task_with_timesheets_ids:
            if len(task_with_timesheets_ids) > 1:
                warning_msg = _("These tasks have some timesheet entries referencing them. Before removing these tasks, you have to remove these timesheet entries.")
            else:
                warning_msg = _("This task has some timesheet entries referencing it. Before removing this task, you have to remove these timesheet entries.")
            raise RedirectWarning(
                warning_msg, self.env.ref('hr_timesheet.timesheet_action_task').id,
                _('See timesheet entries'), {'active_ids': task_with_timesheets_ids})

    @api.model
    def _convert_hours_to_days(self, time):
        uom_hour = self.env.ref('uom.product_uom_hour')
        uom_day = self.env.ref('uom.product_uom_day')
        return round(uom_hour._compute_quantity(time, uom_day, raise_if_failure=False), 2)
