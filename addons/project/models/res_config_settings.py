# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_project_forecast = fields.Boolean(string="Planning")
    module_hr_timesheet = fields.Boolean(string="Task Logs")
    group_subtask_project = fields.Boolean("Sub-tasks", implied_group="project.group_subtask_project")
    group_project_rating = fields.Boolean("Use Rating on Project", implied_group='project.group_project_rating')

    def _get_subtasks_projects_domain(self):
        return []

    def execute(self):
        res = super(ResConfigSettings, self).execute()
        if self.group_project_rating:
            # Change the rating status on existing projects from 'no' to 'stage'
            self.env['project.project'].search([('rating_status', '=', 'no')]).write({
                'rating_status': 'stage'})
        if self.group_subtask_project:
            domain = self._get_subtasks_projects_domain()
            self.env['project.project'].search(domain).write({'allow_subtasks': True})
        return res
