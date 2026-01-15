from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.addons.website_livechat.tests.common import TestLivechatCommon
from odoo.addons.im_livechat.tests.chatbot_common import ChatbotCase


@tagged("post_install", "-at_install")
class TestFwOperator(ChatbotCase, HttpCase, TestLivechatCommon):
    def setUp(self):
        super().setUp()
        self.chatbot_fw_script = self.env["chatbot.script"].create({"title": "Forward Bot"})
        question_step, *_ = tuple(
            self.env["chatbot.script.step"].create(
                [
                    {
                        "chatbot_script_id": self.chatbot_fw_script.id,
                        "message": "Hello, what can I do for you?",
                        "step_type": "question_selection",
                    },
                    {
                        "chatbot_script_id": self.chatbot_fw_script.id,
                        "message": "I'll forward you to an operator.",
                        "step_type": "forward_operator",
                    },
                    {
                        "chatbot_script_id": self.chatbot_fw_script.id,
                        "message": "I could not find an operator to help you.",
                        "step_type": "text",
                    }
                ]
            )
        )
        self.fw_to_operator_answer = self.env["chatbot.script.answer"].create(
            {
                "name": "Forward to operator",
                "script_step_id": question_step.id,
            }
        )
        self.livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Forward to operator channel",
                "rule_ids": [
                    Command.create(
                        {
                            "regex_url": "/",
                            "chatbot_script_id": self.chatbot_fw_script.id,
                        }
                    )
                ],
                "user_ids": [self.operator.id],
            }
        )
        default_website = self.env.ref("website.default_website")
        default_website.channel_id = self.livechat_channel.id

    def test_chatbot_removed_after_forward_to_operator(self):
        self.start_tour("/", "website_livechat.chatbot_forward")
        channel = self.env["discuss.channel"].search(
            [("livechat_channel_id", "=", self.livechat_channel.id)]
        )
        self.assertEqual(channel.livechat_operator_id, self.operator.partner_id)
        self.assertNotIn(
            self.chatbot_fw_script.operator_partner_id, channel.channel_member_ids.partner_id
        )

    def test_chatbot_trigger_blocked_after_forward_to_operator(self):
        data = self.make_jsonrpc_request("/im_livechat/get_session", {
            "channel_id": self.livechat_channel.id,
            "chatbot_script_id": self.chatbot_fw_script.id
        })
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertEqual(channel.chatbot_current_step_id.step_type, "question_selection")
        self._post_answer_and_trigger_next_step(channel, self.fw_to_operator_answer.id)
        self.assertEqual(channel.livechat_operator_id, self.operator.partner_id)
        self.assertEqual(channel.chatbot_current_step_id.step_type, "forward_operator")
        next_step_data = self.make_jsonrpc_request("/chatbot/step/trigger", {"channel_id": channel.id})
        self.assertFalse(next_step_data)
        self.assertEqual(channel.chatbot_current_step_id.step_type, "forward_operator")
