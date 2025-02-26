# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _name = 'res.users.settings'
    _description = 'User Settings'
    _rec_name = 'user_id'

    user_id = fields.Many2one("res.users", string="User", required=True, ondelete="cascade", domain=[("res_users_settings_id", "=", False)])

    _sql_constraints = [
        ('unique_user_id', 'UNIQUE(user_id)', 'One user should only have one user settings.')
    ]

    @api.model
    def _find_or_create_for_user(self, user):
        settings = user.sudo().res_users_settings_ids
        if not settings:
            settings = self.sudo().create({'user_id': user.id})
        return settings

    def _res_users_settings_format(self, fields_to_format=None):
        self.ensure_one()
        if not fields_to_format:
            fields_to_format = [name for name, field in self._fields.items() if name == 'id' or not field.automatic]
        res = self._format_settings(fields_to_format)
        return res

    def _format_settings(self, fields_to_format):
        res = self._read_format(fnames=fields_to_format)[0]
        if 'user_id' in fields_to_format:
            res = self._read_format(fnames=fields_to_format)[0]
            res['user_id'] = {'id': self.user_id.id}
        return res

    def set_res_users_settings(self, new_settings):
        self.ensure_one()
        changed_settings = {}
        for setting in new_settings.keys():
            if setting in self._fields and new_settings[setting] != self[setting]:
                changed_settings[setting] = new_settings[setting]
        self.write(changed_settings)
        formated = self._res_users_settings_format([*changed_settings.keys(), 'id'])
        return formated
