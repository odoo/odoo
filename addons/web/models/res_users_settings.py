from odoo import api, fields, models
from odoo.fields import Domain


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    embedded_actions_config_ids = fields.One2many('res.users.settings.embedded.action', 'user_setting_id')

    @api.model
    def _format_settings(self, fields_to_format):
        res = super()._format_settings(fields_to_format)
        if 'embedded_actions_config_ids' in fields_to_format:
            res['embedded_actions_config_ids'] = self.embedded_actions_config_ids._embedded_action_settings_format()
        return res

    def get_embedded_actions_settings(self, action_ids=None, res_model=None, res_ids=None):
        self.ensure_one()
        domain = Domain('user_setting_id', '=', self.id)
        if isinstance(action_ids, list):
            domain &= Domain('action_id', 'in', action_ids)
        if res_model:
            domain &= Domain('res_model', '=', res_model)
        if isinstance(res_ids, list):
            domain &= Domain('res_id', 'in', res_ids)
        embedded_actions_configs = self.env['res.users.settings.embedded.action'].search(domain)
        return embedded_actions_configs._embedded_action_settings_format()

    def set_embedded_actions_setting(self, action_id, res_id, vals):
        self.ensure_one()
        embedded_actions_config = self.env['res.users.settings.embedded.action'].search([
            ('user_setting_id', '=', self.id), ('action_id', '=', action_id), ('res_id', '=', res_id)
        ], limit=1)
        for field, value in vals.items():
            if field in ('embedded_actions_order', 'embedded_actions_visibility'):
                vals[field] = ','.join('false' if action_id is False else str(action_id) for action_id in value)
        if embedded_actions_config:
            embedded_actions_config.write(vals)
        else:
            self.env['res.users.settings.embedded.action'].create({
                **vals,
                'user_setting_id': self.id,
                'action_id': action_id,
                'res_id': res_id,
            })
