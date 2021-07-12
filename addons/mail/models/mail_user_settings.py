# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailUserSettings(models.Model):
    _name = 'mail.user.settings'
    _description = 'Mail User Settings'

    is_discuss_sidebar_category_channel_open = fields.Boolean(string="Is discuss sidebar category channel open?", default=True)
    is_discuss_sidebar_category_chat_open = fields.Boolean(string="Is discuss sidebar category chat open?", default=True)
    user_id = fields.Many2one('res.users', string="User", required=True, index=True, ondelete='cascade')

    # Rtc
    push_to_talk_key = fields.Char()
    use_push_to_talk = fields.Boolean(default=False)
    voice_active_duration = fields.Integer()
    volume_settings_ids = fields.One2many('mail.volume.setting', 'user_setting_id')

    _sql_constraints = [
        ('unique_user_id', 'UNIQUE(user_id)', 'One user should only have one mail user settings.')
    ]

    @api.model
    def find_or_create_for_user(self, user):
        settings = user.mail_user_settings
        if not settings:
            settings = self.create({'user_id': user.id})
        return settings

    def _mail_user_settings_format_fields(self):
        return [
            'id',
            'is_discuss_sidebar_category_channel_open',
            'is_discuss_sidebar_category_chat_open',
            'user_id',
            'push_to_talk_key',
            'voice_active_duration',
            'use_push_to_talk',
        ]

    def mail_user_settings_format(self):
        self.ensure_one()
        res = self._read_format(fnames=self._mail_user_settings_format_fields())[0]
        res.update({
            'volume_settings': self.volume_settings_ids._read_format(['id', 'user_setting_id', 'partner_id', 'volume']),
        })
        return res

    def set_mail_user_settings(self, new_settings):
        self.ensure_one()
        self.write(new_settings)
        notification = {
            'type': 'mail_user_settings',
            'payload': self.mail_user_settings_format()
        }
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.user_id.partner_id.id), notification)

    def set_volume_setting(self, partner_id, volume):
        self.ensure_one()
        volume_setting = None
        volume_settings = self.volume_settings_ids.filtered(lambda record: record.partner_id.id == partner_id)
        if volume_settings:
            volume_setting = volume_settings[0]
            volume_setting.write({'volume': volume})
        else:
            volume_setting = self.env['mail.volume.setting'].create([{
                'user_setting_id': self.id,
                'partner_id': partner_id,
                'volume': volume,
            }])
        notification = {
            'type': 'mail_volume_setting_update',
            'payload': {
                'volumeSetting': volume_setting.read()[0],
            }
        }
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.user_id.partner_id.id), notification)
