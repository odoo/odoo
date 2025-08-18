from odoo import Command
from odoo.tests import new_test_user
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.tests.common import users, tagged


@tagged("-at_install", "post_install")
class TestImLivechatSessionViews(TestImLivechatCommon):
    def test_session_history_navigation_back_and_forth(self):
        operator = new_test_user(
            self.env,
            login="operator",
            groups="base.group_user,im_livechat.im_livechat_group_manager",
        )
        self.env["mail.presence"]._update_presence(operator)
        self.livechat_channel.user_ids |= operator
        self.authenticate(None, None)
        data = self.make_jsonrpc_request("/im_livechat/get_session", {
            "channel_id": self.livechat_channel.id,
            "previous_operator_id": operator.partner_id.id
        })
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        channel.with_user(operator).message_post(body="Hello, how can I help you?")
        action = self.env.ref("im_livechat.discuss_channel_action_from_livechat_channel")
        self.start_tour(
            f"/odoo/livechat/{self.livechat_channel.id}/action-{action.id}",
            "im_livechat_history_back_and_forth_tour",
            login="operator",
        )

    @users("admin")
    def test_form_view_embed_thread(self):
        operator = new_test_user(
            self.env,
            login="operator",
            groups="base.group_user,im_livechat.im_livechat_group_manager",
        )
        [user_1, user_2] = self.env["res.partner"].create([{"name": "test 1"}, {"name": "test 2"}])
        [channel1, channel2] = self.env["discuss.channel"].create(
            [
                {
                    "name": "test 1",
                    "channel_type": "livechat",
                    "livechat_channel_id": self.livechat_channel.id,
                    "livechat_operator_id": operator.partner_id.id,
                    "channel_member_ids": [Command.create({"partner_id": user_1.id})],
                },
                {
                    "name": "test 2",
                    "channel_type": "livechat",
                    "livechat_channel_id": self.livechat_channel.id,
                    "livechat_operator_id": operator.partner_id.id,
                    "channel_member_ids": [Command.create({"partner_id": user_2.id})],
                },
            ]
        )
        channel1.message_post(
            body="Test Channel 1 Msg", message_type="comment", subtype_xmlid="mail.mt_comment"
        )
        channel2.message_post(
            body="Test Channel 2 Msg", message_type="comment", subtype_xmlid="mail.mt_comment"
        )
        action = self.env.ref("im_livechat.discuss_channel_action_from_livechat_channel")
        self.start_tour(
            f"/odoo/livechat/{self.livechat_channel.id}/action-{action.id}",
            "im_livechat_session_history_open",
            login="operator",
        )

    def test_looking_for_help_real_time_update(self):
        bob = new_test_user(
            self.env,
            login="bob_looking_for_help",
            groups="base.group_user,im_livechat.im_livechat_group_user",
        )
        self.livechat_channel.user_ids |= bob
        self.authenticate(None, None)
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": self.livechat_channel.id, "previous_operator_id": bob.partner_id.id},
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        chat.livechat_status = "need_help"
        looking_for_help_action = self.env.ref(
            "im_livechat.discuss_channel_looking_for_help_action"
        )
        self.start_tour(
            f"/odoo/action-{looking_for_help_action.id}",
            "im_livechat.looking_for_help_list_real_time_update_tour",
            login="bob_looking_for_help",
        )
        self.start_tour(
            f"/odoo/action-{looking_for_help_action.id}?view_type=kanban",
            "im_livechat.looking_for_help_kanban_real_time_update_tour",
            login="bob_looking_for_help",
        )
