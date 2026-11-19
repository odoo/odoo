from odoo import models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    def get_embedded_actions_settings(self):
        embedded_actions_settings_dict = super().get_embedded_actions_settings()
        res_model = self.env.context.get('res_model')
        res_id = self.env.context.get('res_id')
        if not (res_model == 'project.project' and res_id):
            return embedded_actions_settings_dict

        if self.user_id.has_group('project.group_project_manager'):
            action = self.env.ref('project.act_project_project_2_project_task_all')
            config_key = f'{action.id}+{res_id}'

            if config_key not in embedded_actions_settings_dict:
                overview = self.env.ref('project.project_embedded_action_project_overview')
                config = {
                    'embedded_actions_visibility': [False, overview.id],
                    'embedded_actions_order': [],
                    'embedded_visibility': True,
                }
                self.set_embedded_actions_setting(action.id, res_id, {
                    'res_model': res_model,
                    **config,
                })
                embedded_actions_settings_dict[config_key] = config

        project_manager = self.env['project.project'].browse(res_id).user_id
        if self.user_id == project_manager:
            return embedded_actions_settings_dict

        user_configs = self.env['res.users.settings.embedded.action'].search(
            domain=[
                ('user_setting_id', '=', self.id),
                ('res_model', '=', res_model),
                ('res_id', '=', res_id),
            ],
        )
        manager_configs_sudo = self.env['res.users.settings.embedded.action'].sudo().search(
            domain=[
                ('user_setting_id', '=', project_manager.sudo().res_users_settings_id.id),
                ('res_model', '=', res_model),
                ('res_id', '=', res_id),
                ('action_id', 'not in', user_configs.action_id.ids),
            ],
        )
        if manager_configs_sudo:
            embedded_actions_settings_dict.update(manager_configs_sudo.copy({'user_setting_id': self.id})._embedded_action_settings_format())

        return embedded_actions_settings_dict
