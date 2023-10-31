# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectDelete(models.TransientModel):
    _name = 'project.delete.wizard'
    _description = 'Project Delete Wizard'

    project_ids = fields.Many2many('project.project', string='Projects')
    task_count = fields.Integer(compute='_compute_task_count')
    projects_archived = fields.Boolean(compute='_compute_projects_archived')

    def _compute_projects_archived(self):
        for wizard in self.with_context(active_test=False):
            wizard.projects_archived = all(not p.active for p in wizard.project_ids)

    def _compute_task_count(self):
        for wizard in self:
            wizard.task_count = sum(wizard.with_context(active_test=False).project_ids.mapped('task_count'))

    def action_archive(self):
        self.project_ids.write({'active': False})

    def confirm_delete(self):
        self.with_context(active_test=False).project_ids.unlink()
        return self.env["project.project"]._action_open_all_projects()
