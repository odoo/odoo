# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectDelete(models.TransientModel):
    _name = 'project.delete.wizard'
    _description = 'Project Delete Wizard'

    project_ids = fields.Many2many('project.project', string='Projects')
    task_count = fields.Integer(compute='_compute_task_count')

    def _compute_task_count(self):
        for wizard in self:
            wizard.task_count = sum(wizard.with_context(active_test=False).project_ids.mapped('task_count'))

    def action_archive(self):
        self.project_ids.write({'active': False})
        return self.env.ref('project.open_view_project_all').read()[0]

    def confirm_delete(self):
        self.with_context(active_test=False).project_ids.unlink()
        return self.env.ref('project.open_view_project_all').read()[0]
