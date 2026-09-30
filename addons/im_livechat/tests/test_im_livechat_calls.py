# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import wraps
from unittest.mock import patch

from odoo.tests.common import tagged
from odoo.addons.im_livechat.controllers.main import LivechatController
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


@tagged("post_install", "-at_install")
class TestImLivechatCalls(TestImLivechatCommon):
    def test_meeting_view(self):
        og_get_session = LivechatController.get_session

        def _patched_get_session(*args, **kwargs):
            result = og_get_session(*args, **kwargs)
            if kwargs["persisted"]:
                self.env.flush_all()
                channel = self.env["discuss.channel"].search([("id", "=", result["channel_id"])])
                agent = channel.channel_member_ids.filtered(lambda m: m.partner_id)
                agent.sudo()._rtc_join_call()
            return result

        with patch.object(LivechatController, "get_session", wraps(og_get_session)(_patched_get_session)):
            self.start_tour(
                f"/im_livechat/support/{self.livechat_channel.id}",
                "im_livechat.meeting_view_tour",
            )
