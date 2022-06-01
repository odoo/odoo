# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResUsersSettings(models.Model):
    _name = 'res.users.settings'
    _description = 'User Settings'

    user_id = fields.Many2one('res.users', string="User", required=True, readonly=True, ondelete='cascade')
    is_discuss_sidebar_category_channel_open = fields.Boolean(string="Is discuss sidebar category channel open?", default=True)
    is_discuss_sidebar_category_chat_open = fields.Boolean(string="Is discuss sidebar category chat open?", default=True)

    # RTC
    push_to_talk_key = fields.Char(string="Push-To-Talk shortcut", help="String formatted to represent a key with modifiers following this pattern: shift.ctrl.alt.key, e.g: truthy.1.true.b")
    use_push_to_talk = fields.Boolean(string="Use the push to talk feature", default=False)
    voice_active_duration = fields.Integer(string="Duration of voice activity in ms", help="How long the audio broadcast will remain active after passing the volume threshold")
    volume_settings_ids = fields.One2many('res.users.settings.volumes', 'user_setting_id', string="Volumes of other partners")

    _sql_constraints = [
        ('unique_user_id', 'UNIQUE(user_id)', 'One user should only have one mail user settings.')
    ]

    @api.model
    def _find_or_create_for_user(self, user):
        settings = user.sudo().res_users_settings_ids
        if not settings:
            settings = self.sudo().create({'user_id': user.id})
        return settings

    def _get_rename_table(self):
        return {
            'is_discuss_sidebar_category_channel_open': 'isDiscussSidebarCategoryChannelOpen',
            'is_discuss_sidebar_category_chat_open': 'isDiscussSidebarCategoryChatOpen',
            'push_to_talk_key': 'pushToTalkKey',
            'use_push_to_talk': 'usePushToTalk',
            'voice_active_duration': 'voiceActiveDuration',
        }

    def _res_users_settings_format(self):
        self.ensure_one()
        volume_settings = self.volume_settings_ids._discuss_users_settings_volume_format()
        return {
            'id': self.id,
            'isDiscussSidebarCategoryChannelOpen': self.is_discuss_sidebar_category_channel_open,
            'isDiscussSidebarCategoryChatOpen': self.is_discuss_sidebar_category_chat_open,
            'pushToTalkKey': self.push_to_talk_key,
            'usePushToTalk': self.use_push_to_talk,
            'voiceActiveDuration': self.voice_active_duration,
            'volumeSettings': [('insert', volume_settings)] if volume_settings else [],
        }

    def set_res_users_settings(self, new_settings):
        self.ensure_one()
        fields_to_update = {}
        for field_name, new_value in new_settings.items():
            if not field_name in self._fields:
                raise UserError(_("'%(field_name)s' is not a valid user setting.", field_name=field_name))
            if new_value != self[field_name]:
                fields_to_update[field_name] = new_value
        self.write(fields_to_update)
        formatted_fields = {}
        rename_table = self._get_rename_table()
        # Rename fields to match their client-side name.
        for field_name in fields_to_update:
            new_name = rename_table[field_name] if field_name in rename_table else field_name
            formatted_fields[new_name] = self[field_name]
        self.env['bus.bus']._sendone(self.user_id.partner_id, 'res.users.settings/changed', formatted_fields)

    def set_volume_setting(self, partner_id, volume, guest_id=None):
        """
        Saves the volume of a guest or a partner.
        Either partner_id or guest_id must be specified.
        :param float volume: the selected volume between 0 and 1
        :param int partner_id:
        :param int guest_id:
        """
        self.ensure_one()
        volume_setting = self.env['res.users.settings.volumes'].search([
            ('user_setting_id', '=', self.id), ('partner_id', '=', partner_id), ('guest_id', '=', guest_id)
        ])
        if volume_setting:
            volume_setting.volume = volume
        else:
            volume_setting = self.env['res.users.settings.volumes'].create({
                'user_setting_id': self.id,
                'volume': volume,
                'partner_id': partner_id,
                'guest_id': guest_id,
            })
        self.env['bus.bus']._sendone(self.user_id.partner_id, 'res.users.settings/volumes_update', {
            'volumeSettings': [('insert', volume_setting._discuss_users_settings_volume_format())],
        })
