# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo.http import request
from odoo.addons.mail.controllers.discuss.rtc import RtcController
from odoo.addons.mail.tools.discuss import mail_route


class LivechatRtcController(RtcController):
    @mail_route()
    def channel_call_join(self, channel_id, check_rtc_session_ids=None, camera=False):
        # sudo: discuss.channel - visitor can check if there is an ongoing call
        if not request.env.user._is_internal() and request.env["discuss.channel"].sudo().search([
            ("id", "=", channel_id),
            ("channel_type", "=", "livechat"),
            ("rtc_session_ids", "=", False),
        ]):
            raise NotFound()
        return super().channel_call_join(channel_id, check_rtc_session_ids, camera)
