# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.http import request, route, Controller


class DiscussSettingsController(Controller):
    @route("/discuss/settings/mute", methods=["POST"], type="jsonrpc", auth="user")
    def discuss_mute(self, minutes, channel_id=None):
        """Mute notifications for the given number of minutes.
        :param minutes: (integer) number of minutes to mute notifications, -1 means mute until the user unmutes
        :param channel_id: (integer) id of the discuss.channel record, if not set, mute for res.users.settings
        """
        if not channel_id:
            record = request.env['res.users.settings']._find_or_create_for_user(request.env.user)
        else:
            channel = request.env["discuss.channel"].browse(channel_id)
            if not channel:
                raise request.not_found()
            record = channel._find_or_create_member_for_self()
        if not record:
            raise request.not_found()
        if minutes == -1:
            record.mute_until_dt = datetime.max
        elif minutes:
            record.mute_until_dt = fields.Datetime.now() + relativedelta(minutes=minutes)
        else:
            record.mute_until_dt = False
        record._notify_mute()

    @route("/discuss/settings/custom_notifications", methods=["POST"], type="jsonrpc", auth="user")
    def discuss_custom_notifications(self, custom_notifications, channel_id=None):
        """Set custom notifications for the given channel or general user settings.
        :param custom_notifications: (false|all|mentions|no_notif) custom notifications to set
        :param channel_id: (integer) id of the discuss.channel record, if not set, set for res.users.settings
        """
        if not channel_id:
            record = request.env['res.users.settings']._find_or_create_for_user(request.env.user)
        else:
            channel = request.env["discuss.channel"].browse(channel_id)
            if not channel:
                raise request.not_found()
            record = channel._find_or_create_member_for_self()
        if not record:
            raise request.not_found()
        record.set_custom_notifications(custom_notifications)

    @route("/discuss/settings/whatsapp_mute_toggle", methods=["POST"], type="jsonrpc", auth="user")
    def discuss_whatsapp_mute_toggle(self, shouldMute, minutes):
        """
        Handles toggling the mute state for all WhatsApp channels for the current user
        and updates the global flag.
        :param mute_state: (boolean) True to mute, False to unmute.
        """
        user = request.env.user
        settings = request.env['res.users.settings']._find_or_create_for_user(user)
        if not settings:
            raise request.not_found()
        settings.set_res_users_settings({'mute_all_whatsapp': shouldMute})
        if shouldMute and minutes != -1:
            target_dt = fields.Datetime.now() + relativedelta(minutes=minutes)
        elif shouldMute and minutes:
            target_dt = datetime.max
        else:
            target_dt = False
        whatsapp_member_domain = [
            ('partner_id', '=', user.partner_id.id),
            ('channel_id.channel_type', '=', 'whatsapp')
        ]
        whatsapp_members = request.env['discuss.channel.member'].search(whatsapp_member_domain)
        if whatsapp_members:
            whatsapp_members.write({'mute_until_dt': target_dt})
            for member in whatsapp_members:
                member._notify_mute()
        return True
