from datetime import timedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import new_test_user, tagged
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


@tagged("-at_install", "post_install")
class TestDiscussChannel(TestImLivechatCommon):
    def test_unfollow_from_non_member_does_not_close_livechat(self):
        bob_user = new_test_user(
            self.env, "bob_user", groups="base.group_user,im_livechat.im_livechat_group_manager"
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "anonymous_name": "Visitor",
            },
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertTrue(chat.livechat_active)
        chat.with_user(bob_user).action_unfollow()
        self.assertTrue(chat.livechat_active)
        chat.with_user(chat.livechat_operator_id.user_ids[0]).action_unfollow()
        self.assertFalse(chat.livechat_active)

    def test_human_operator_failure_states(self):
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "anonymous_name": "Visitor",
            },
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertFalse(chat.chatbot_current_step_id)  # assert there is no chatbot
        self.assertEqual(chat.livechat_failure, "no_answer")
        chat.with_user(chat.livechat_operator_id.user_ids[0]).message_post(
            body="I am here to help!",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertEqual(chat.livechat_failure, "no_failure")

    def test_chatbot_failure_states(self):
        chatbot_script = self.env["chatbot.script"].create({"title": "Testing Bot"})
        self.livechat_channel.rule_ids = [(0, 0, {"chatbot_script_id": chatbot_script.id})]
        self.env["chatbot.script.step"].create({
            "step_type": "forward_operator",
            "message": "I will transfer you to a human.",
            "chatbot_script_id": chatbot_script.id,
        })
        bob_operator = new_test_user(
            self.env, "bob_user", groups="im_livechat.im_livechat_group_user"
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "anonymous_name": "Visitor",
                "chatbot_script_id": chatbot_script.id,
                "channel_id": self.livechat_channel.id,
            },
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertTrue(chat.chatbot_current_step_id)  # assert there is a chatbot
        self.assertEqual(chat.livechat_failure, "no_failure")
        self.livechat_channel.user_ids = False  # remove operators so forwarding will fail
        chat.chatbot_current_step_id._process_step_forward_operator(chat)
        self.assertEqual(chat.livechat_failure, "no_agent")
        self.livechat_channel.user_ids += bob_operator
        self.assertTrue(self.livechat_channel.available_operator_ids)
        chat.chatbot_current_step_id._process_step_forward_operator(chat)
        self.assertEqual(chat.livechat_operator_id, bob_operator.partner_id)
        self.assertEqual(chat.livechat_failure, "no_answer")
        chat.with_user(bob_operator).message_post(
            body="I am here to help!",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertEqual(chat.livechat_failure, "no_failure")

    def test_livechat_conversation_history(self):
        """Test livechat conversation history formatting"""
        self.authenticate(self.operators[0].login, self.password)
        channel = self.env["discuss.channel"].create(
            {
                "name": "test",
                "channel_type": "livechat",
                "livechat_operator_id": self.operators[0].partner_id.id,
                "channel_member_ids": [
                    Command.create({"partner_id": self.operators[0].partner_id.id}),
                    Command.create({"partner_id": self.visitor_user.partner_id.id}),
                ],
            }
        )
        attachment1 = self.env["ir.attachment"].create({"name": "test.txt"})
        attachment2 = self.env["ir.attachment"].with_user(self.visitor_user).create({"name": "test2.txt"})
        channel.message_post(body="Operator Here")
        channel.message_post(body="", attachment_ids=[attachment1.id])
        channel.with_user(self.visitor_user).message_post(body="Visitor Here")
        channel.with_user(self.visitor_user).message_post(body="", attachment_ids=[attachment2.id])
        channel_history = channel._get_channel_history()
        self.assertEqual(channel_history, 'Operator Here<br/>Visitor Here<br/>')

    def test_gc_bot_sessions_after_one_day_inactivity(self):
        chatbot_script = self.env["chatbot.script"].create({"title": "Testing Bot"})
        self.livechat_channel.rule_ids = [Command.create({"chatbot_script_id": chatbot_script.id})]
        self.env["chatbot.script.step"].create({
            "chatbot_script_id": chatbot_script.id,
            "message": "Hello joey, how you doing?",
            "step_type": "text",
        })
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "anonymous_name": "Thomas",
                "chatbot_script_id": chatbot_script.id,
                "channel_id": self.livechat_channel.id,
            },
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        with freeze_time(fields.Datetime.to_string(fields.Datetime.now() + timedelta(hours=23))):
            self.assertTrue(channel.livechat_active)
        with freeze_time(fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=1))):
            channel._gc_bot_only_ongoing_sessions()
        self.assertFalse(channel.livechat_active)
