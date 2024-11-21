# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import format_date

from .project_task import CLOSED_STATES

class ProjectMilestone(models.Model):
    _name = 'project.milestone'
    _description = "Project Milestone"
    _inherit = ['mail.thread']
    _order = 'deadline, is_reached desc, name'

    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')

    name = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True, default=_get_default_project_id, ondelete='cascade')
    deadline = fields.Date(tracking=True, copy=False)
    is_reached = fields.Boolean(string="Reached", default=False, copy=False)
    reached_date = fields.Date(compute='_compute_reached_date', store=True, export_string_translation=False)
    task_ids = fields.One2many('project.task', 'milestone_id', 'Tasks', export_string_translation=False)

    # computed non-stored fields
    is_deadline_exceeded = fields.Boolean(compute="_compute_is_deadline_exceeded", export_string_translation=False)
    is_deadline_future = fields.Boolean(compute="_compute_is_deadline_future", export_string_translation=False)
    task_count = fields.Integer('# of Tasks', compute='_compute_task_count', groups='project.group_project_milestone, export_string_translation=False')
    done_task_count = fields.Integer('# of Done Tasks', compute='_compute_task_count', groups='project.group_project_milestone', export_string_translation=False)
    can_be_marked_as_done = fields.Boolean(compute='_compute_can_be_marked_as_done', export_string_translation=False)

    @api.depends('is_reached')
    def _compute_reached_date(self):
        for ms in self:
            ms.reached_date = ms.is_reached and fields.Date.context_today(self)

    @api.depends('is_reached', 'deadline')
    def _compute_is_deadline_exceeded(self):
        today = fields.Date.context_today(self)
        for ms in self:
            ms.is_deadline_exceeded = not ms.is_reached and ms.deadline and ms.deadline < today

    @api.depends('deadline')
    def _compute_is_deadline_future(self):
        for ms in self:
            ms.is_deadline_future = ms.deadline and ms.deadline > fields.Date.context_today(self)

    @api.depends('task_ids.milestone_id')
    def _compute_task_count(self):
        all_and_done_task_count_per_milestone = {
            milestone.id: (count, sum(state in CLOSED_STATES for state in state_list))
            for milestone, count, state_list in self.env['project.task']._read_group(
                [('milestone_id', 'in', self.ids), ('allow_milestones', '=', True)],
                ['milestone_id'], ['__count', 'state:array_agg'],
            )
        }
        for milestone in self:
            milestone.task_count, milestone.done_task_count = all_and_done_task_count_per_milestone.get(milestone.id, (0, 0))

    def _compute_can_be_marked_as_done(self):
        if not any(self._ids):
            for milestone in self:
                milestone.can_be_marked_as_done = not milestone.is_reached and all(milestone.task_ids.mapped(lambda t: t.is_closed))
            return

        unreached_milestones = self.filtered(lambda milestone: not milestone.is_reached)
        (self - unreached_milestones).can_be_marked_as_done = False
        task_read_group = self.env['project.task']._read_group(
            [('milestone_id', 'in', unreached_milestones.ids)],
            ['milestone_id', 'state'],
            ['__count'],
        )
        task_count_per_milestones = defaultdict(lambda: (0, 0))
        for milestone, state, count in task_read_group:
            opened_task_count, closed_task_count = task_count_per_milestones[milestone.id]
            if state in CLOSED_STATES:
                closed_task_count += count
            else:
                opened_task_count += count
            task_count_per_milestones[milestone.id] = opened_task_count, closed_task_count
        for milestone in unreached_milestones:
            opened_task_count, closed_task_count = task_count_per_milestones[milestone.id]
            milestone.can_be_marked_as_done = closed_task_count > 0 and not opened_task_count

    def toggle_is_reached(self, is_reached):
        self.ensure_one()
        self.update({'is_reached': is_reached})
        return self._get_data()

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('project.action_view_task_from_milestone')
        action['context'] = {'default_project_id': self.project_id.id, 'default_milestone_id': self.id}
        if self.task_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.task_ids.id
            if 'views' in action:
                action['views'] = [(view_id, view_type) for view_id, view_type in action['views'] if view_type == 'form']
        return action

    @api.model
    def _get_fields_to_export(self):
        return ['id', 'name', 'deadline', 'is_reached', 'reached_date', 'is_deadline_exceeded', 'is_deadline_future', 'can_be_marked_as_done']

    def _get_data(self):
        self.ensure_one()
        return {field: self[field] for field in self._get_fields_to_export()}

    def _get_data_list(self):
        return [ms._get_data() for ms in self]

    def copy(self, default=None):
        default = dict(default or {})
        new_milestones = super().copy(default)
        milestone_mapping = self.env.context.get('milestone_mapping', {})
        for old_milestone, new_milestone in zip(self, new_milestones):
            if old_milestone.project_id.allow_milestones:
                milestone_mapping[old_milestone.id] = new_milestone.id
        return new_milestones

    def _compute_display_name(self):
        super()._compute_display_name()
        if not self._context.get('display_milestone_deadline'):
            return
        for milestone in self:
            if milestone.deadline:
                milestone.display_name = f'{milestone.display_name} - {format_date(self.env, milestone.deadline)}'
