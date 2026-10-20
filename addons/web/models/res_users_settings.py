from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    hub_config_ids = fields.One2many('res.users.settings.hub', 'user_setting_id')

    @api.model
    def _format_settings(self, fields_to_format):
        res = super()._format_settings(fields_to_format)
        if 'hub_config_ids' in fields_to_format:
            res['hub_config_ids'] = {
                f'{setting.hub_id.id},{setting.res_id}': {
                    'pinned_item_ids': setting.pinned_item_ids or [],
                    'show_tabs': setting.show_tabs,
                }
                for setting in self.hub_config_ids
            }
        return res

    def get_default_hub_setting(self, hub_id, res_id):
        """ Return the setting (see ``set_hub_setting``) the user starts from for
        the hub ``hub_id`` opened for the record ``res_id``, when they have none
        yet. Meant to be overridden, e.g. to start from the setting of another
        user.
        """
        self.ensure_one()
        return {}

    def set_hub_setting(self, hub_id, res_id, vals):
        """ Save the setting ``vals`` (pinned items and/or tabs visibility) of
        the user for the hub ``hub_id`` opened for the record ``res_id``.
        """
        self.ensure_one()
        vals = {key: vals[key] for key in ('pinned_item_ids', 'show_tabs') if key in vals}
        hub_config = self.env['res.users.settings.hub'].search([
            ('user_setting_id', '=', self.id), ('hub_id', '=', hub_id), ('res_id', '=', res_id)
        ], limit=1)
        if hub_config:
            hub_config.write(vals)
        else:
            self.env['res.users.settings.hub'].create({
                **vals,
                'user_setting_id': self.id,
                'hub_id': hub_id,
                'res_id': res_id,
            })
