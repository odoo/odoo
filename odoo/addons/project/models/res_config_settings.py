# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_hr_timesheet = fields.Boolean(string="Task Logs")
    group_project_rating = fields.Boolean("Customer Ratings", implied_group='project.group_project_rating')
    group_project_stages = fields.Boolean("Project Stages", implied_group="project.group_project_stages")
    group_project_recurring_tasks = fields.Boolean("Recurring Tasks", implied_group="project.group_project_recurring_tasks")
    group_project_task_dependencies = fields.Boolean("Task Dependencies", implied_group="project.group_project_task_dependencies")
    group_project_milestone = fields.Boolean('Milestones', implied_group='project.group_project_milestone', group='base.group_portal,base.group_user')

    # Analytic Accounting
    analytic_plan_id = fields.Many2one(
        comodel_name='account.analytic.plan',
        string="Analytic Plan",
        config_parameter="analytic.analytic_plan_projects",
    )

    @api.model
    def _get_basic_project_domain(self):
        return []

    def set_values(self):
        # Ensure that settings on existing projects match the above fields
        projects = self.env["project.project"].search([])
        basic_projects = projects.filtered_domain(self._get_basic_project_domain())

        features = {
            # key: (config_flag, is_global), value: project_flag
            ("group_project_rating", True): "rating_active",
            ("group_project_task_dependencies", False): "allow_task_dependencies",
            ("group_project_milestone", False): "allow_milestones",
        }

        for (config_flag, is_global), project_flag in features.items():
            config_flag_global = f"project.{config_flag}"
            config_feature_enabled = self[config_flag]
            if self.user_has_groups(config_flag_global) != config_feature_enabled:
                if config_feature_enabled and not is_global:
                    basic_projects[project_flag] = config_feature_enabled
                else:
                    projects[project_flag] = config_feature_enabled

        task_waiting_subtype_id = self.env.ref('project.mt_task_waiting')
        project_task_waiting_subtype_id = self.env.ref('project.mt_project_task_waiting')
        if task_waiting_subtype_id.hidden != (not self['group_project_task_dependencies']):
            task_waiting_subtype_id.hidden = not self['group_project_task_dependencies']
            project_task_waiting_subtype_id.hidden = not self['group_project_task_dependencies']
        # Hide Project Stage Changed mail subtype according to the settings
        project_stage_change_mail_type = self.env.ref('project.mt_project_stage_change')
        if project_stage_change_mail_type.hidden == self['group_project_stages']:
            project_stage_change_mail_type.hidden = not self['group_project_stages']
        # Hide task rating tempalate when customer rating is disbled
        task_rating_subtype_id = self.env.ref('project.mt_project_task_rating')
        task_rating_subtype_id.hidden = not self['group_project_rating']
        self.env.ref('project.mt_task_rating').hidden = not self['group_project_rating']
        task_rating_subtype_id.default = self['group_project_rating']
        rating_project_request_email_template = self.env.ref('project.rating_project_request_email_template')
        if rating_project_request_email_template.active != self['group_project_rating']:
            rating_project_request_email_template.active = self['group_project_rating']
        if not self['group_project_recurring_tasks']:
            self.env['project.task'].sudo().search([('recurring_task', '=', True)]).write({'recurring_task': False})

        super().set_values()
