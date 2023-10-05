# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    is_discuss_sidebar_category_channel_open = fields.Boolean(string="Is discuss sidebar category channel open?", default=True)
    is_discuss_sidebar_category_chat_open = fields.Boolean(string="Is discuss sidebar category chat open?", default=True)

    # RTC
    push_to_talk_key = fields.Char(string="Push-To-Talk shortcut", help="String formatted to represent a key with modifiers following this pattern: shift.ctrl.alt.key, e.g: truthy.1.true.b")
    use_push_to_talk = fields.Boolean(string="Use the push to talk feature", default=False)
    voice_active_duration = fields.Integer(string="Duration of voice activity in ms", help="How long the audio broadcast will remain active after passing the volume threshold")
    volume_settings_ids = fields.One2many('res.users.settings.volumes', 'user_setting_id', string="Volumes of other partners")

    @api.model
    def _format_settings(self, fields_to_format):
        res = super()._format_settings(fields_to_format)
        if 'volume_settings_ids' in fields_to_format:
            volume_settings = self.volume_settings_ids._discuss_users_settings_volume_format()
            res['volume_settings_ids'] = [('ADD', volume_settings)]
        return res

    def set_res_users_settings(self, new_settings):
        formated = super().set_res_users_settings(new_settings)
        self.env['bus.bus']._sendone(self.user_id.partner_id, 'res.users.settings', formated)
        return formated

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
        self.env['bus.bus']._sendone(self.user_id.partner_id, 'res.users.settings.volumes', volume_setting._discuss_users_settings_volume_format())
