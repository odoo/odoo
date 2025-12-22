# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo.http import route, request
from odoo.addons.mail.controllers.discuss.rtc import RtcController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class LivechatRtcController(RtcController):
    @route()
    @add_guest_to_context
    def channel_call_join(self, channel_id, check_rtc_session_ids=None, camera=False):
        if request.env.user.is_public and request.env["discuss.channel"].search([
            ("id", "=", channel_id),
            ("channel_type", "=", "livechat"),
            ("rtc_session_ids", "=", False),
        ]):
            raise NotFound()
        return super().channel_call_join(channel_id, check_rtc_session_ids, camera)
