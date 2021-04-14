# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ProjectMilestone(models.Model):
    _name = 'project.milestone'
    _description = "Project Milestone"
    _inherit = ['mail.thread']
    _order = 'deadline, is_reached desc, name'

    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')

    name = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True, default=_get_default_project_id)
    deadline = fields.Date(tracking=True)
    is_reached = fields.Boolean(string="Reached", default=False)
    reached_date = fields.Date(compute='_compute_reached_date', store=True)

    # computed non-stored fields
    is_deadline_exceeded = fields.Boolean(compute="_compute_is_deadline_exceeded")
    is_deadline_future = fields.Boolean(compute="_compute_is_deadline_future")

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

    def toggle_is_reached(self, is_reached):
        self.ensure_one()
        self.update({'is_reached': is_reached})
        return self._get_data()

    @api.model
    def _get_fields_to_export(self):
        return ['id', 'name', 'deadline', 'is_reached', 'reached_date', 'is_deadline_exceeded', 'is_deadline_future']

    def _get_data(self):
        self.ensure_one()
        return {field: self[field] for field in self._get_fields_to_export()}

    def _get_data_list(self):
        return [ms._get_data() for ms in self]
