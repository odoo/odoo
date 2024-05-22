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

        # Ensure that settings on existing projects match the above fields
        projects = self.env["project.project"].search([])
        features = (
            # Pairs of associated (config_flag, project_flag)
            ("group_subtask_project", "allow_subtasks"),
            ("group_project_rating", "rating_active"),
            ("group_project_recurring_tasks", "allow_recurring_tasks"),
            )
        for (config_flag, project_flag) in features:
            config_flag_global = "project." + config_flag
            config_feature_enabled = self[config_flag]
            if (self.user_has_groups(config_flag_global)
                    is not config_feature_enabled):
                projects[project_flag] = config_feature_enabled

        super(ResConfigSettings, self).set_values()
