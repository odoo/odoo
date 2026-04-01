from odoo.addons.im_livechat.tests import chatbot_common
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, new_test_user
from odoo.addons.im_livechat.tests.common import TestGetOperatorCommon


@tagged("post_install", "-at_install")
class TestLivechatMemberHistory(TestGetOperatorCommon, chatbot_common.ChatbotCase):
    def test_get_session_create_history(self):
        john = self._create_operator("fr_FR")
        bob = self._create_operator("fr_FR")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [bob.id],
            },
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": livechat_channel.id}
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertEqual(len(channel.channel_member_ids.livechat_member_history_ids), 2)
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id == bob.partner_id
            ).livechat_member_type,
            "agent",
        )
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id != bob.partner_id
            ).livechat_member_type,
            "visitor",
        )
        channel.add_members(partner_ids=john.partner_id.ids)
        self.assertEqual(len(channel.channel_member_ids.livechat_member_history_ids), 3)
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id == john.partner_id
            ).livechat_member_type,
            "agent",
        )

    def test_get_session_create_history_with_bot(self):
        john = self._create_operator("fr_FR")
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "chatbot_script_id": self.chatbot_script.id,
                "channel_id": self.livechat_channel.id,
            },
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertEqual(len(channel.channel_member_ids.livechat_member_history_ids), 2)
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id == self.chatbot_script.operator_partner_id
            ).livechat_member_type,
            "bot",
        )
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id != self.chatbot_script.operator_partner_id
            ).livechat_member_type,
            "visitor",
        )
        channel.add_members(partner_ids=john.partner_id.ids)
        self.assertEqual(len(channel.channel_member_ids.livechat_member_history_ids), 3)
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id == john.partner_id
            ).livechat_member_type,
            "agent",
        )

    def test_marked_as_visitor_when_joining_after_log_in(self):
        self.authenticate(None, None)
        john = self._create_operator("fr_FR")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": john.ids,
            },
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": livechat_channel.id}
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertEqual(len(channel.channel_member_ids.livechat_member_history_ids), 2)
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id == john.partner_id,
            ).livechat_member_type,
            "agent",
        )
        guest_visitor_history = channel.channel_member_ids.livechat_member_history_ids.filtered(
            lambda m: m.guest_id
        )
        self.assertEqual(guest_visitor_history.livechat_member_type, "visitor")
        visitor_user = new_test_user(
            self.env, login="visitor_user", groups="im_livechat.im_livechat_group_manager"
        )
        self.authenticate("visitor_user", "visitor_user")
        data = self.make_jsonrpc_request(
            "/discuss/channel/notify_typing",
            {"channel_id": channel.id, "is_typing": True},
            cookies={
                guest_visitor_history.guest_id._cookie_name: guest_visitor_history.guest_id._format_auth_cookie()
            },
        )
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id == visitor_user.partner_id,
            ).livechat_member_type,
            "visitor",
        )

    def test_can_only_create_history_for_livechats(self):
        john = self._create_operator("fr_FR")
        channel = self.env["discuss.channel"]._create_channel(name="General", group_id=None)
        member = channel.add_members(partner_ids=john.partner_id.ids)
        with self.assertRaises(ValidationError):
            self.env["im_livechat.channel.member.history"].create({"member_id": member.id}).channel_id

    def test_update_history_on_second_join(self):
        john = self._create_operator("fr_FR")
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Livechat Channel", "user_ids": [john.id]},
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": livechat_channel.id},
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        og_history = channel.channel_member_ids.livechat_member_history_ids.filtered(
            lambda m: m.partner_id == john.partner_id
        )
        john_member = channel.channel_member_ids.filtered(lambda m: m.partner_id == john.partner_id)
        self.assertEqual(og_history.livechat_member_type, "agent")
        self.assertEqual(og_history.member_id, john_member)
        channel.with_user(john).action_unfollow()
        john_history = channel.channel_member_ids.livechat_member_history_ids.filtered(
            lambda m: m.partner_id == john.partner_id
        )
        self.assertFalse(john_history.member_id)
        self.assertNotIn(john.partner_id, channel.channel_member_ids.partner_id)
        channel._add_members(users=john)
        self.assertIn(john.partner_id, channel.channel_member_ids.partner_id)
        john_member = channel.channel_member_ids.filtered(lambda m: m.partner_id == john.partner_id)
        john_history = channel.channel_member_ids.livechat_member_history_ids.filtered(
            lambda m: m.partner_id == john.partner_id
        )
        self.assertEqual(og_history, john_history)
        self.assertEqual(john_member, john_history.member_id)
