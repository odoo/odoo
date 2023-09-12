# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.controllers.discuss.rtc import RtcController


class LivechatRtcController(RtcController):
    @route("/mail/rtc/session/notify_call_members", cors="*")
    @add_guest_to_context
    def session_call_notify(self, peer_notifications):
        return super().session_call_notify(peer_notifications)

    @route("/mail/rtc/session/update_and_broadcast", cors="*")
    @add_guest_to_context
    def session_update_and_broadcast(self, session_id, values):
        return super().session_update_and_broadcast(session_id, values)

    @route("/mail/rtc/channel/join_call", cors="*")
    @add_guest_to_context
    def channel_call_join(self, channel_id, check_rtc_session_ids=None):
        return super().channel_call_join(channel_id, check_rtc_session_ids=check_rtc_session_ids)

    @route("/mail/rtc/channel/leave_call", cors="*")
    @add_guest_to_context
    def channel_call_leave(self, channel_id):
        return super().channel_call_leave(channel_id)

    @route("/discuss/channel/ping", cors="*")
    @add_guest_to_context
    def channel_ping(self, channel_id, rtc_session_id=None, check_rtc_session_ids=None):
        return super().channel_ping(channel_id, rtc_session_id=rtc_session_id, check_rtc_session_ids=check_rtc_session_ids)
