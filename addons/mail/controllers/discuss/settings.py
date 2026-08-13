# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.http import request, route, Controller


class DiscussSettingsController(Controller):
    @route("/discuss/settings/mute", methods=["POST"], type="json", auth="user")
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

    @route("/discuss/settings/custom_notifications", methods=["POST"], type="json", auth="user")
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
