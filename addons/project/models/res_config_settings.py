# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_project_forecast = fields.Boolean(string="Planning")
    module_hr_timesheet = fields.Boolean(string="Task Logs")
    group_subtask_project = fields.Boolean("Sub-tasks", implied_group="project.group_subtask_project")
    group_project_rating = fields.Boolean("Customer Ratings", implied_group='project.group_project_rating')
    group_project_stages = fields.Boolean("Project Stages", implied_group="project.group_project_stages")
    group_project_recurring_tasks = fields.Boolean("Recurring Tasks", implied_group="project.group_project_recurring_tasks")
    group_project_task_dependencies = fields.Boolean("Task Dependencies", implied_group="project.group_project_task_dependencies")

    @api.model
    def _get_basic_project_domain(self):
        return []

    def set_values(self):
        # Ensure that settings on existing projects match the above fields
        projects = self.env["project.project"].search([])
        global_features = {  # key: config_flag, value: project_flag
            "group_project_rating": "rating_active",
            "group_project_recurring_tasks": "allow_recurring_tasks",
        }
        basic_project_features = {
            "group_subtask_project": "allow_subtasks",
            "group_project_task_dependencies": "allow_task_dependencies",
        }
        config_feature_vals = {config_flag: self[config_flag]
                               for config_flag in global_features.keys() | basic_project_features.keys()}

        def update_projects(projects, features):
            for (config_flag, project_flag) in features.items():
                config_flag_global = "project." + config_flag
                config_feature_enabled = config_feature_vals[config_flag]
                if self.user_has_groups(config_flag_global) != config_feature_enabled:
                    projects[project_flag] = config_feature_enabled

        # update for all projects
        update_projects(projects, global_features)
        # update for basic projects
        update_projects(projects.filtered_domain(self._get_basic_project_domain()), basic_project_features)

        # Hide the task dependency changes subtype when the dependency setting is disabled
        task_dep_change_subtype_id = self.env.ref('project.mt_task_dependency_change')
        project_task_dep_change_subtype_id = self.env.ref('project.mt_project_task_dependency_change')
        if task_dep_change_subtype_id.hidden != (not self['group_project_task_dependencies']):
            task_dep_change_subtype_id.hidden = not self['group_project_task_dependencies']
            project_task_dep_change_subtype_id.hidden = not self['group_project_task_dependencies']
        # Hide Project Stage Changed mail subtype according to the settings
        project_stage_change_mail_type = self.env.ref('project.mt_project_stage_change')
        if project_stage_change_mail_type.hidden == self['group_project_stages']:
            project_stage_change_mail_type.hidden = not self['group_project_stages']

        super(ResConfigSettings, self).set_values()
