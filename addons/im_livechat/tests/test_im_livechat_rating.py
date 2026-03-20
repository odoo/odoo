# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.im_livechat.tests.common import TestGetOperatorCommon


class TestImLivechatFeedback(TestGetOperatorCommon):
    def test_rating_is_associated_to_agent(self):
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
            {"channel_id": chat.id, "rate": 5, "reason": "Good service"},
        )
        self.assertEqual(chat.rating_ids.rated_partner_id, agent.partner_id)
