# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.im_livechat.tests import chatbot_common
from odoo.exceptions import ValidationError
from odoo.tests.common import get_db_name, new_test_user
from odoo.addons.im_livechat.tests.common import TestGetOperatorCommon


class TestLivechatMemberHistory(TestGetOperatorCommon, chatbot_common.ChatbotCase):
    def test_history_modified_only_for_active_livechat(self):
        john = self._create_operator("fr_FR")
        bob = self._create_operator("fr_FR")
        michel = self._create_operator("fr_FR")
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
        channel._add_members(users=john)
        self.assertEqual(len(channel.channel_member_ids.livechat_member_history_ids), 3)
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id == john.partner_id
            ).livechat_member_type,
            "agent",
        )
        channel.livechat_end_dt = fields.Datetime.now()
        channel._add_members(users=michel)
        self.assertEqual(len(channel.channel_member_ids.livechat_member_history_ids), 3)

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
        channel._add_members(users=john)
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

    def test_livechat_membership_added_on_login(self):
        self.authenticate(None, None)
        visitor = new_test_user(self.env, login="batman_visitor", groups="base.group_portal")
        operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create({
            "name": "Livechat Channel",
            "user_ids": operator.ids,
        })
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": livechat_channel.id}
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        guest = channel.channel_member_ids.guest_id
        guest_message_data = self.make_jsonrpc_request(
            "/mail/message/post",
            {
                "post_data": {"body": "Help me", "message_type": "comment"},
                "thread_model": "discuss.channel",
                "thread_id": channel.id,
            },
            cookies={guest._cookie_name: guest._format_auth_cookie()},
        )
        guest_message = self.env["mail.message"].browse(guest_message_data["message_id"]).sudo()
        agent_message = channel.with_user(operator).message_post(
            body="how can I help you?",
            message_type="comment",
        ).sudo()
        self.make_jsonrpc_request(
            "/mail/message/reaction",
            {"action": "add", "content": "👍", "message_id": guest_message.id},
            cookies={guest._cookie_name: guest._format_auth_cookie()},
        )
        self.make_jsonrpc_request(
            "/mail/message/reaction",
            {"action": "add", "content": "👍", "message_id": agent_message.id},
            cookies={guest._cookie_name: guest._format_auth_cookie()},
        )
        self.make_jsonrpc_request(
            "/web/session/authenticate",
            {
                "db": get_db_name(),
                "login": visitor.login,
                "password": visitor.login,
            },
            cookies={guest._cookie_name: guest._format_auth_cookie()},
        )
        visitor_member = channel.channel_member_ids.filtered(lambda c: c.partner_id == visitor.partner_id)
        self.assertEqual(visitor_member.livechat_member_type, "visitor")
        self.assertEqual(len(channel.channel_member_ids), 2)
        self.assertEqual(len(channel.livechat_channel_member_history_ids), 3)
        self.assertEqual(
            channel.channel_member_ids.livechat_member_history_ids.filtered(
                lambda m: m.partner_id == visitor.partner_id,
            ).livechat_member_type,
            "visitor",
        )
        self.assertEqual(guest_message.author_id, visitor.partner_id)
        self.assertFalse(guest_message.author_guest_id)
        self.assertEqual(guest_message.reaction_ids.partner_id, visitor.partner_id)
        self.assertFalse(guest_message.reaction_ids.guest_id)
        self.assertEqual(agent_message.reaction_ids.partner_id, visitor.partner_id)
        self.assertFalse(agent_message.reaction_ids.guest_id)

    def test_can_only_create_history_for_livechats(self):
        john = self._create_operator("fr_FR")
        channel = self.env["discuss.channel"]._create_channel(name="General", group_id=None)
        member = channel._add_members(users=john)
        with self.assertRaises(ValidationError):
            self.env["im_livechat.channel.member.history"].create({"member_id": member.id}).channel_id

    def test_update_history_on_second_join(self):
        john = self._create_operator("fr_FR")
        bob = self._create_operator("fr_FR")
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
        # Add another agent so the channel stays active and the history can be updated.
        channel._add_members(users=bob)
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
