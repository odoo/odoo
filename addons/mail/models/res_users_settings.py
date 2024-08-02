# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    is_discuss_sidebar_category_channel_open = fields.Boolean(string="Is discuss sidebar category channel open?", default=True)
    is_discuss_sidebar_category_chat_open = fields.Boolean(string="Is discuss sidebar category chat open?", default=True)

    # RTC
    push_to_talk_key = fields.Char(string="Push-To-Talk shortcut", help="String formatted to represent a key with modifiers following this pattern: shift.ctrl.alt.key, e.g: truthy.1.true.b")
    use_push_to_talk = fields.Boolean(string="Use the push to talk feature", default=False)
    voice_active_duration = fields.Integer(string="Duration of voice activity in ms", default=200, help="How long the audio broadcast will remain active after passing the volume threshold")
    volume_settings_ids = fields.One2many('res.users.settings.volumes', 'user_setting_id', string="Volumes of other partners")

    # Notifications
    channel_notifications = fields.Selection(
        [("all", "All Messages"), ("no_notif", "Nothing")],
        "Channel Notifications",
        help="This setting will only be applied to channels. Mentions only if not specified.",
    )
    mute_until_dt = fields.Datetime(string="Mute notifications until", index=True, help="If set, the user will not receive notifications from all the channels until this date.")

    @api.model
    def _cleanup_expired_mutes(self):
        """
        Cron job for cleanup expired unmute by resetting mute_until_dt and sending bus notifications.
        """
        settings = self.search([("mute_until_dt", "<=", fields.Datetime.now())])
        settings.write({"mute_until_dt": False})
        settings._notify_mute()

    @api.model
    def _format_settings(self, fields_to_format):
        res = super()._format_settings(fields_to_format)
        if 'volume_settings_ids' in fields_to_format:
            volume_settings = self.volume_settings_ids._discuss_users_settings_volume_format()
            res.pop('volume_settings_ids', None)
            res['volumes'] = [('ADD', volume_settings)]
        if "mute_until_dt" in fields_to_format:
            res["mute_until_dt"] = fields.Datetime.to_string(self.mute_until_dt)
        return res

    def _notify_mute(self):
        for setting in self:
            setting._bus_send("res.users.settings", {"mute_until_dt": setting.mute_until_dt})
            if setting.mute_until_dt and setting.mute_until_dt != -1:
                self.env.ref("mail.ir_cron_discuss_users_settings_unmute")._trigger(setting.mute_until_dt)

    def set_custom_notifications(self, custom_notifications):
        self.set_res_users_settings({"channel_notifications": custom_notifications})

    def set_res_users_settings(self, new_settings):
        formatted = super().set_res_users_settings(new_settings)
        self._bus_send("res.users.settings", formatted)
        return formatted

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
        self._bus_send(
            "res.users.settings.volumes", volume_setting._discuss_users_settings_volume_format()
        )
