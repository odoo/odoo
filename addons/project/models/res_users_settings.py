from odoo import models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    def get_embedded_actions_setting(self, action_id, res_id):
        self.ensure_one()
        if action_id == self.env.ref('project.act_project_project_2_project_task_all').id:
            current_user_config = self.env['res.users.settings.embedded.action'].search([
                ('user_setting_id', '=', self.id), ('action_id', '=', action_id), ('res_id', '=', res_id)
            ], limit=1)
            if not current_user_config:
                project_manager = self.env['project.project'].browse(res_id).user_id
                if self.user_id != project_manager:
                    project_manager_config = self.env['res.users.settings.embedded.action'].sudo().search([
                        ('user_setting_id', 'in', project_manager.sudo().res_users_settings_ids.ids), ('action_id', '=', action_id), ('res_id', '=', res_id)
                    ], limit=1)
                    if project_manager_config:
                        return project_manager_config.copy({'user_setting_id': self.id})._embedded_action_settings_format()
        return super().get_embedded_actions_setting(action_id, res_id)
