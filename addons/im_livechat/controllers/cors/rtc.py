# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.discuss.rtc import RtcController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class LivechatRtcController(RtcController):
    @route("/im_livechat/cors/rtc/channel/join_call", methods=["POST"], type="jsonrpc", auth="public", cors="*")
    def livechat_channel_call_join(self, guest_token, channel_id, check_rtc_session_ids=None):
        force_guest_env(guest_token)
        return self.channel_call_join(channel_id, check_rtc_session_ids)

    @route("/im_livechat/cors/rtc/channel/leave_call", methods=["POST"], type="jsonrpc", auth="public", cors="*")
    def livechat_channel_call_leave(self, guest_token, channel_id):
        force_guest_env(guest_token)
        return self.channel_call_leave(channel_id)

    @route("/im_livechat/cors/rtc/session/update_and_broadcast", methods=["POST"], type="jsonrpc", auth="public", cors="*")
    def livechat_session_update_and_broadcast(self, guest_token, session_id, values):
        force_guest_env(guest_token)
        self.session_update_and_broadcast(session_id, values)

    @route("/im_livechat/cors/rtc/session/notify_call_members", methods=["POST"], type="jsonrpc", auth="public", cors="*")
    def livechat_session_call_notify(self, guest_token, peer_notifications):
        force_guest_env(guest_token)
        self.session_call_notify(peer_notifications)

    @route("/im_livechat/cors/channel/ping", methods=["POST"], type="jsonrpc", auth="public", cors="*")
    def livechat_channel_ping(self, guest_token, channel_id, rtc_session_id=None, check_rtc_session_ids=None):
        force_guest_env(guest_token)
        return self.channel_ping(channel_id, rtc_session_id, check_rtc_session_ids)
