from odoo import Command, tests
from odoo.addons.test_mail_full.tests.test_portal import TestPortal
from odoo.addons.website_livechat.tests.test_chatbot_ui import TestLivechatChatbotUI


@tests.common.tagged("post_install", "-at_install")
class TestImLivechatPortal(TestLivechatChatbotUI, TestPortal):
    def test_chatbot_redirect_to_portal(self):
        chatbot_redirect_script = self.env["chatbot.script"].create({"title": "Redirection Bot"})
        question_step = self.env["chatbot.script.step"].create(
            [
                {
                    "chatbot_script_id": chatbot_redirect_script.id,
                    "message": "Hello, were do you want to go?",
                    "step_type": "question_selection",
                },
                {
                    "chatbot_script_id": chatbot_redirect_script.id,
                    "message": "Tadam, we are on the page you asked for!",
                    "step_type": "text",
                },
            ]
        )[0]
        self.env["chatbot.script.answer"].create(
            [
                {
                    "name": "Go to the portal page",
                    "redirect_link": f"/my/test_portal_records/{self.record_portal.id}",
                    "script_step_id": question_step.id,
                },
            ]
        )
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Redirection Channel",
                "rule_ids": [
                    Command.create(
                        {
                            "regex_url": "/",
                            "chatbot_script_id": chatbot_redirect_script.id,
                        }
                    )
                ],
            }
        )
        default_website = self.env.ref("website.default_website")
        default_website.channel_id = livechat_channel.id
        self.env.ref("website.default_website").channel_id = livechat_channel.id
        self.start_tour("/contactus", "test_mail_full.chatbot_redirect_to_portal")
