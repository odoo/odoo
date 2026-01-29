import json
from datetime import timedelta
from freezegun import freeze_time
from markupsafe import Markup

from odoo import Command, fields
from odoo.tests import new_test_user, tagged, users
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
        chat._forward_human_operator(chat.chatbot_current_step_id)
        self.assertEqual(chat.livechat_failure, "no_agent")
        self.livechat_channel.user_ids += bob_operator
        self.assertTrue(self.livechat_channel.available_operator_ids)
        chat._forward_human_operator(chat.chatbot_current_step_id)
        self.assertEqual(chat.livechat_operator_id, bob_operator.partner_id)
        self.assertEqual(chat.livechat_failure, "no_answer")
        chat.with_user(bob_operator).message_post(
            body="I am here to help!",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertEqual(chat.livechat_failure, "no_failure")

    def test_livechat_description_sync_to_internal_user_bus(self):
        """Test the description of a livechat conversation is sent to the internal user bus."""
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
                                "description": "Description of the conversation",
                            }
                        ]
                    },
                }
            ],
        ):
            channel.description = "Description of the conversation"

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

    @users("michel")
    def test_livechat_conversation_history(self):
        """Test livechat conversation history formatting"""
        def _convert_attachment_to_html(attachment):
            attachment_data = {
                "id": attachment.id,
                "access_token": attachment.access_token,
                "checksum": attachment.checksum,
                "extension": "txt",
                "mimetype": attachment.mimetype,
                "filename": attachment.display_name,
                "url": attachment.url,
            }
            return Markup(
                "<div data-embedded='file' data-oe-protected='true' contenteditable='false' data-embedded-props='%s'/>",
            ) % json.dumps({"fileData": attachment_data})

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
        channel.message_post(body="Operator Here", message_type="comment")
        channel.message_post(body="", message_type="comment", attachment_ids=[attachment1.id])
        channel.with_user(self.visitor_user).message_post(body="Visitor Here", message_type="comment")
        channel.with_user(self.visitor_user).message_post(body="", message_type="comment", attachment_ids=[attachment2.id])
        channel.message_post(body="Some notification", message_type="notification")
        channel_history = channel.with_user(self.visitor_user)._get_channel_history()
        self.assertEqual(
            channel_history,
            "<br/><strong>Michel Operator:</strong><br/>Operator Here<br/>%(attachment_1)s<br/>"
            "<br/><strong>Rajesh:</strong><br/>Visitor Here<br/>%(attachment_2)s<br/>"
            % {
                "attachment_1": _convert_attachment_to_html(attachment1),
                "attachment_2": _convert_attachment_to_html(attachment2),
            },
        )

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
            self.assertFalse(channel.livechat_end_dt)
        with freeze_time(fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=1))):
            channel._gc_bot_only_ongoing_sessions()
        self.assertTrue(channel.livechat_end_dt)

    def test_expertises_added_from_discuss_are_kept(self):
        bob = self._create_operator()
        jane = self._create_operator()
        dog_expertise = self.env["im_livechat.expertise"].create({"name": "Dog"})
        operator_expertise_ids = dog_expertise
        chatbot_script = self.env["chatbot.script"].create({"title": "Testing Bot"})
        self.env["chatbot.script.step"].create(
            [
                {
                    "chatbot_script_id": chatbot_script.id,
                    "message": "Hello, how can I help you?",
                    "step_type": "free_input_single",
                },
                {
                    "chatbot_script_id": chatbot_script.id,
                    "operator_expertise_ids": operator_expertise_ids,
                    "step_type": "forward_operator",
                },
            ]
        )
        self.livechat_channel.user_ids = jane
        self.livechat_channel.rule_ids = [Command.create({"chatbot_script_id": chatbot_script.id})]
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "chatbot_script_id": chatbot_script.id,
                "channel_id": self.livechat_channel.id,
            },
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        self.make_jsonrpc_request(
            "/chatbot/step/trigger",
            {"channel_id": channel.id, "chatbot_script_id": chatbot_script.id},
        )
        self.assertIn(jane.partner_id, channel.livechat_agent_history_ids.partner_id)
        self.assertEqual(channel.livechat_expertise_ids, operator_expertise_ids)
        cat_expertise = self.env["im_livechat.expertise"].create({"name": "Cat"})
        self.authenticate(jane.login, jane.login)
        self.make_jsonrpc_request(
            "/im_livechat/conversation/write_expertises",
            {
                "channel_id": channel.id,
                "orm_commands": [Command.link(cat_expertise.id)],
            },
        )
        self.assertEqual(channel.livechat_expertise_ids, operator_expertise_ids | cat_expertise)
        channel._add_members(users=bob)
        self.assertEqual(channel.livechat_expertise_ids, operator_expertise_ids | cat_expertise)
