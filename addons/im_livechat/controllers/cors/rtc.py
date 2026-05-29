# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.mail.controllers.discuss.rtc import RtcController


class LivechatRtcController(RtcController):
    @route(
        "/im_livechat/cors/rtc/channel/join_call",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_channel_call_join(self, guest_token, channel_id, check_rtc_session_ids=None):
        return self.channel_call_join(channel_id, check_rtc_session_ids)

    @route(
        "/im_livechat/cors/rtc/channel/leave_call",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_channel_call_leave(self, guest_token, channel_id):
        return self.channel_call_leave(channel_id)

    @route(
        "/im_livechat/cors/rtc/session/update_and_broadcast",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_session_update_and_broadcast(self, guest_token, session_id, values):
        self.session_update_and_broadcast(session_id, values)

    @route(
        "/im_livechat/cors/rtc/session/notify_call_members",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_session_call_notify(self, guest_token, peer_notifications):
        self.session_call_notify(peer_notifications)

    @route(
        "/im_livechat/cors/channel/ping",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_channel_ping(
        self,
        guest_token,
        channel_id,
        rtc_session_id=None,
        check_rtc_session_ids=None,
    ):
        return self.channel_ping(channel_id, rtc_session_id, check_rtc_session_ids)
