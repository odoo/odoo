# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.im_livechat.tests.common import TestGetOperatorCommon
from odoo.tests.common import JsonRpcException
from odoo.tools.misc import mute_logger


class TestImLivechatFeedback(TestGetOperatorCommon):
    def test_rating_allowed_for_visitor(self):
        agent = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Test Livechat Channel", "user_ids": [agent.id]},
        )
        self.authenticate(None, None)
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": livechat_channel.id, "persisted": True},
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        self.make_jsonrpc_request(
            "/im_livechat/feedback",
            {"channel_id": chat.id, "rate": 5, "reason": "Great support!"},
        )
        self.assertEqual(chat.livechat_rating, "5")

    @mute_logger("odoo.http")
    def test_rating_not_allowed_for_agent(self):
        agent = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Test Livechat Channel", "user_ids": [agent.id]},
        )
        self.authenticate(None, None)
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": livechat_channel.id, "persisted": True},
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        self.authenticate(agent.login, "operator_password")
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                "/im_livechat/feedback",
                {"channel_id": chat.id, "rate": 5, "reason": "Excellent!"},
            )
        self.assertFalse(chat.livechat_rating)
