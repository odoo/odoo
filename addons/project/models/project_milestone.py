# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models

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
    reached_date = fields.Date(compute='_compute_reached_date', store=True)
    task_ids = fields.One2many('project.task', 'milestone_id', 'Tasks')

    # computed non-stored fields
    is_deadline_exceeded = fields.Boolean(compute="_compute_is_deadline_exceeded")
    is_deadline_future = fields.Boolean(compute="_compute_is_deadline_future")
    task_count = fields.Integer('# of Tasks', compute='_compute_task_count', groups='project.group_project_milestone')
    can_be_marked_as_done = fields.Boolean(compute='_compute_can_be_marked_as_done', groups='project.group_project_milestone')

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
        task_read_group = self.env['project.task']._read_group([('milestone_id', 'in', self.ids), ('allow_milestones', '=', True)], ['milestone_id'], ['milestone_id'])
        task_count_per_milestone = {res['milestone_id'][0]: res['milestone_id_count'] for res in task_read_group}
        for milestone in self:
            milestone.task_count = task_count_per_milestone.get(milestone.id, 0)

    def _compute_can_be_marked_as_done(self):
        if not any(self._ids):
            for milestone in self:
                milestone.can_be_marked_as_done = not milestone.is_reached and all(milestone.task_ids.is_closed)
            return
        unreached_milestones = self.filtered(lambda milestone: not milestone.is_reached)
        (self - unreached_milestones).can_be_marked_as_done = False
        if unreached_milestones:
            task_read_group = self.env['project.task']._read_group(
                [('milestone_id', 'in', unreached_milestones.ids)],
                ['milestone_id', 'is_closed', 'task_count:count(id)'],
                ['milestone_id', 'is_closed'],
                lazy=False,
            )
            task_count_per_milestones = defaultdict(lambda: (0, 0))
            for res in task_read_group:
                opened_task_count, closed_task_count = task_count_per_milestones[res['milestone_id'][0]]
                if res['is_closed']:
                    closed_task_count += res['task_count']
                else:
                    opened_task_count += res['task_count']
                task_count_per_milestones[res['milestone_id'][0]] = opened_task_count, closed_task_count
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

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        milestone_copy = super(ProjectMilestone, self).copy(default)
        if self.project_id.allow_milestones:
            milestone_mapping = self.env.context.get('milestone_mapping', {})
            milestone_mapping[self.id] = milestone_copy.id
        return milestone_copy
