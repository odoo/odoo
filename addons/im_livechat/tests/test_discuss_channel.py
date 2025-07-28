from odoo.tests import new_test_user, tagged
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon, TestGetOperatorCommon
from odoo.addons.mail.tests.common import MailCase


@tagged("-at_install", "post_install")
class TestDiscussChannel(TestImLivechatCommon, TestGetOperatorCommon, MailCase):
    def test_unfollow_from_non_member_does_not_close_livechat(self):
        bob_user = new_test_user(
            self.env, "bob_user", groups="base.group_user,im_livechat.im_livechat_group_manager"
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": self.livechat_channel.id}
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertFalse(chat.livechat_end_dt)
        chat.with_user(bob_user).action_unfollow()
        self.assertFalse(chat.livechat_end_dt)
        chat.with_user(chat.livechat_operator_id.main_user_id).action_unfollow()
        self.assertTrue(chat.livechat_end_dt)

    def test_human_operator_failure_states(self):
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": self.livechat_channel.id}
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertFalse(chat.chatbot_current_step_id)  # assert there is no chatbot
        self.assertEqual(chat.livechat_failure, "no_answer")
        chat.with_user(chat.livechat_operator_id.main_user_id).message_post(
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
            {"chatbot_script_id": chatbot_script.id, "channel_id": self.livechat_channel.id},
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

    def test_livechat_note_sync_to_internal_user_bus(self):
        """Test that a livechat note is sent to the internal user bus."""
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": self.livechat_channel.id},
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        with self.assertBus(
            [(self.cr.dbname, "discuss.channel", channel.id, "internal_users")],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "livechat_note": [
                                    "markup",
                                    "<p>This is a note for the internal user.</p>",
                                ],
                            }
                        ]
                    },
                }
            ],
        ):
            channel.livechat_note = "This is a note for the internal user."

    def test_livechat_status_sync_to_internal_user_bus(self):
        """Test that a livechat status is sent to the internal user bus."""
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": self.livechat_channel.id},
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        with self.assertBus(
            [(self.cr.dbname, "discuss.channel", channel.id, "internal_users")],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "livechat_status": "waiting",
                            }
                        ]
                    },
                }
            ],
        ):
            channel.livechat_status = "waiting"

    def test_livechat_status_switch_on_operator_joined_batch(self):
        """Test that the livechat status switches to 'in_progress' when an operator joins multiple channels in a batch,
        and ensure re-adding the same member does not change the status."""
        channel_1 = self.env["discuss.channel"].create({
            "name": "Livechat Channel 1",
            "channel_type": "livechat",
            "livechat_operator_id": self.operators[0].partner_id.id,
        })
        channel_2 = self.env["discuss.channel"].create({
            "name": "Livechat Channel 2",
            "channel_type": "livechat",
            "livechat_operator_id": self.operators[0].partner_id.id,
        })
        bob_operator = new_test_user(self.env, "bob_user", groups="im_livechat.im_livechat_group_user")
        channel_1.livechat_status = "need_help"
        channel_2.livechat_status = "need_help"
        self.assertEqual(channel_1.livechat_status, "need_help")
        self.assertEqual(channel_2.livechat_status, "need_help")
        self.assertFalse(channel_1.livechat_end_dt)
        self.assertFalse(channel_2.livechat_end_dt)

        # Add the operator to both channels in a batch, which should switch their status to 'in_progress'
        (channel_1 | channel_2).with_user(channel_1.livechat_operator_id.main_user_id).add_members(
            partner_ids=bob_operator.partner_id.ids
        )
        self.assertEqual(channel_1.livechat_status, "in_progress")
        self.assertEqual(channel_2.livechat_status, "in_progress")

        # Re-add the same operator and ensure the status does not change
        channel_1.livechat_status = "need_help"
        self.assertEqual(channel_1.livechat_status, "need_help")
        channel_1.with_user(channel_1.livechat_operator_id.main_user_id).add_members(
            partner_ids=bob_operator.partner_id.ids
        )
        self.assertEqual(channel_1.livechat_status, "need_help")

    def test_join_livechat_needing_help(self):
        bob = self._create_operator()
        john = self._create_operator()
        jane = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Livechat Channel", "user_ids": (bob + jane + john).ids},
        )
        chat = self._create_conversation(livechat_channel, bob)
        chat.livechat_status = "need_help"
        has_joined = chat.with_user(john).livechat_join_channel_needing_help()
        self.assertTrue(has_joined)
        self.assertIn(john.partner_id, chat.channel_member_ids.partner_id)
        self.assertEqual(chat.livechat_status, "in_progress")
        has_joined = chat.with_user(jane).livechat_join_channel_needing_help()
        self.assertFalse(has_joined)
        self.assertNotIn(jane.partner_id, chat.channel_member_ids.partner_id)
