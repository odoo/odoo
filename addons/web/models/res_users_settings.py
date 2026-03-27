from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    embedded_actions_config_ids = fields.One2many('res.users.settings.embedded.action', 'user_setting_id')

    @api.model
    def _format_settings(self, fields_to_format):
        res = super()._format_settings(fields_to_format)
        if 'embedded_actions_config_ids' in fields_to_format:
            res['embedded_actions_config_ids'] = self.embedded_actions_config_ids._embedded_action_settings_format()
        return res

    def get_embedded_actions_settings(self):
        self.ensure_one()
        return self.embedded_actions_config_ids._embedded_action_settings_format()

    def set_embedded_actions_setting(self, action_id, res_id, vals):
        self.ensure_one()
        embedded_actions_config = self.env['res.users.settings.embedded.action'].search([
            ('user_setting_id', '=', self.id), ('action_id', '=', action_id), ('res_id', '=', res_id)
        ], limit=1)
        new_vals = {}
        for field, value in vals.items():
            if field in ('embedded_actions_order', 'embedded_actions_visibility'):
                new_vals[field] = ','.join('false' if action_id is False else str(action_id) for action_id in value)
            else:
                new_vals[field] = value
        if embedded_actions_config:
            embedded_actions_config.write(new_vals)
        else:
            self.env['res.users.settings.embedded.action'].create({
                **new_vals,
                'user_setting_id': self.id,
                'action_id': action_id,
                'res_id': res_id,
            })
