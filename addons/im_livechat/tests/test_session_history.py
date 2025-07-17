# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import new_test_user, tagged
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


@tagged("-at_install", "post_install")
class TestImLivechatSessionHistory(TestImLivechatCommon):
    def test_session_history_navigation_back_and_forth(self):
        operator = new_test_user(self.env, login="operator", groups="base.group_user,im_livechat.im_livechat_group_manager")
        self.env["bus.presence"].create({"user_id": operator.id, "status": "online"})
        self.livechat_channel.user_ids |= operator
        self.authenticate(None, None)
        data = self.make_jsonrpc_request("/im_livechat/get_session", {
            "channel_id": self.livechat_channel.id,
            "anonymous_name": "Visitor",
            "previous_operator_id": operator.partner_id.id
        })
        channel = self.env["discuss.channel"].browse(data["discuss.channel"][0]["id"])
        channel.with_user(operator).message_post(body="Hello, how can I help you?")
        action = self.env.ref("im_livechat.discuss_channel_action_from_livechat_channel")
        self.start_tour(
            f"/odoo/livechat/{self.livechat_channel.id}/action-{action.id}",
            "im_livechat_history_back_and_forth_tour",
            login="operator",
        )

    def test_livechat_operator_cannot_access_other_operator_session(self):
        member = new_test_user(self.env, login="member")
        agent = new_test_user(self.env, login="agent")
        channel = self.env["discuss.channel"].create(
            {
                "channel_type": "livechat",
                "livechat_operator_id": member.partner_id.id,
                "name": "test",
                "channel_member_ids": [Command.create({"partner_id": member.partner_id.id})],
            },
        )
        rating = self.env["rating.rating"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("discuss.channel"),
                "res_id": channel.id,
            },
        )
        self.assertEqual(
            rating.with_user(member).action_open_rated_object().get("tag"),
            "mail.action_discuss",
        )
        self.assertEqual(
            rating.with_user(self.operators[0]).action_open_rated_object().get("tag"),
            "mail.action_discuss",
        )
        self.assertNotEqual(
            rating.with_user(agent).action_open_rated_object().get("tag"),
            "mail.action_discuss",
        )
