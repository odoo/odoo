# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _name = 'res.users.settings'
    _description = 'User Settings'

    user_id = fields.Many2one('res.users', string="User", required=True, readonly=True, ondelete='cascade')
    is_discuss_sidebar_category_channel_open = fields.Boolean(string="Is discuss sidebar category channel open?", default=True)
    is_discuss_sidebar_category_chat_open = fields.Boolean(string="Is discuss sidebar category chat open?", default=True)

    _sql_constraints = [
        ('unique_user_id', 'UNIQUE(user_id)', 'One user should only have one mail user settings.')
    ]

    @api.model
    def _find_or_create_for_user(self, user):
        settings = user.res_users_settings_ids
        if not settings:
            settings = self.create({'user_id': user.id})
        return settings

    def _res_users_settings_format(self):
        self.ensure_one()
        return self._read_format(fnames=[name for name, field in self._fields.items() if name == 'id' or not field.automatic])[0]

    def set_res_users_settings(self, new_settings):
        self.ensure_one()
        changed_settings = {}
        for setting in new_settings.keys():
            if setting in self._fields and new_settings[setting] != self[setting]:
                changed_settings[setting] = new_settings[setting]
        self.write(changed_settings)
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.user_id.partner_id.id), {
            'type': 'res.users_settings_changed',
            'payload': changed_settings,
        })
