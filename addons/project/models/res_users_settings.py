from odoo import models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    def get_default_hub_setting(self, hub_id, res_id):
        """ Start from the pinned items of the project manager on a project. """
        res = super().get_default_hub_setting(hub_id, res_id)
        hub = self.env['ir.hub'].browse(hub_id)
        if hub.res_model != 'project.project':
            return res
        project_manager = self.env['project.project'].browse(res_id).exists().user_id
        if not project_manager or project_manager == self.user_id:
            return res
        # sudo: the settings of the project manager are not readable by the user
        manager_setting_sudo = self.env['res.users.settings.hub'].sudo().search([
            ('user_setting_id.user_id', '=', project_manager.id),
            ('hub_id', '=', hub_id),
            ('res_id', '=', res_id),
        ], limit=1)
        if manager_setting_sudo.pinned_item_ids:
            res['pinned_item_ids'] = manager_setting_sudo.pinned_item_ids
        return res
