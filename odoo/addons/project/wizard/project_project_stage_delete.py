# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from odoo import api, fields, models

class ProjectStageDelete(models.TransientModel):
    _name = 'project.project.stage.delete.wizard'
    _description = 'Project Stage Delete Wizard'

    stage_ids = fields.Many2many('project.project.stage', string='Stages To Delete', ondelete='cascade', context={'active_test': False})
    projects_count = fields.Integer('Number of Projects', compute='_compute_projects_count')
    stages_active = fields.Boolean(compute='_compute_stages_active')

    def _compute_projects_count(self):
        for wizard in self:
            wizard.projects_count = self.with_context(active_test=False).env['project.project'].search_count([('stage_id', 'in', wizard.stage_ids.ids)])

    @api.depends('stage_ids')
    def _compute_stages_active(self):
        for wizard in self:
            wizard.stages_active = all(wizard.stage_ids.mapped('active'))

    def action_archive(self):
        projects = self.with_context(active_test=False).env['project.project'].search([('stage_id', 'in', self.stage_ids.ids)])
        projects.write({'active': False})
        self.stage_ids.write({'active': False})
        return self._get_action()

    def action_unarchive_project(self):
        inactive_projects = self.env['project.project'].with_context(active_test=False).search(
            [('active', '=', False), ('stage_id', 'in', self.stage_ids.ids)])
        inactive_projects.action_unarchive()

    def action_unlink(self):
        self.stage_ids.unlink()
        return self._get_action()

    def _get_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("project.project_project_stage_configure")\
              if self.env.context.get('stage_view')\
            else self.env["ir.actions.actions"]._for_xml_id("project.open_view_project_all_group_stage")

        context = action.get('context', '{}')
        context = context.replace('uid', str(self.env.uid))
        context = dict(literal_eval(context), active_test=True)
        action['context'] = context
        action['target'] = 'main'
        return action
