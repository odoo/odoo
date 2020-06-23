# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_project_forecast = fields.Boolean(string="Planning")
    module_hr_timesheet = fields.Boolean(string="Task Logs")
    group_subtask_project = fields.Boolean("Sub-tasks", implied_group="project.group_subtask_project")
    group_project_rating = fields.Boolean("Customer Ratings", implied_group='project.group_project_rating')
    group_project_recurring_tasks = fields.Boolean("Recurring Tasks", implied_group="project.group_project_recurring_tasks")

    def set_values(self):
        if self.user_has_groups('project.group_project_recurring_tasks') != self.group_project_recurring_tasks:
            self.env['project.project'].sudo().search([]).write({'allow_recurring_tasks': self.group_project_recurring_tasks})
        super(ResConfigSettings, self).set_values()
