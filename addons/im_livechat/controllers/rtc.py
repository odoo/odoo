from werkzeug.exceptions import NotFound

from odoo.http import request, route

from odoo.addons.mail.controllers.discuss.rtc import RtcController
from odoo.addons.mail.tools.discuss import add_guest_to_context


class LivechatRtcController(RtcController):
    @route()
    @add_guest_to_context
    def channel_call_join(self, channel_id, check_rtc_session_ids=None, camera=False):
        if not request.env.user._is_internal() and request.env[
            "discuss.channel"
        ].sudo().search(
            [
                ("id", "=", channel_id),
                ("channel_type", "=", "livechat"),
                ("rtc_session_ids", "=", False),
            ]
        ):
            raise NotFound
        return super().channel_call_join(channel_id, check_rtc_session_ids, camera)
