# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.website_livechat.tests.test_chatbot_ui import TestLivechatChatbotUI


class TestImLivechatPortal(TestLivechatChatbotUI):
    def test_chatbot_redirect_to_portal(self):
        project = self.env["project.project"].create({"name": "Portal Project"})
        task = self.env["project.task"].create(
            {"name": "Test Task Name Match", "project_id": project.id}
        )
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
                    "redirect_link": f"/my/tasks/{task.id}?access_token={task.access_token}",
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
        default_website = self.env.ref("base.default_website")
        default_website.channel_id = livechat_channel.id
        self.env.ref("base.default_website").channel_id = livechat_channel.id
        self.start_tour("/contactus", "chatbot_redirect_to_portal")

    def test_portal_chatter_reaction_with_livechat(self):
        task = self.env["project.task"].create(
            {
                "name": "Test Task",
                "partner_id": self.env["res.partner"].create({"name": "Task Customer"}).id,
                "project_id": self.env["project.project"].create({"name": "Portal Project"}).id,
            },
        )
        task.message_post(
            body="Message on the task",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.livechat_channel.rule_ids = [Command.clear(), Command.create({"regex_url": "/"})]
        self.start_tour(
            f"/my/tasks/{task.id}?access_token={task.access_token}",
            "portal_chatter_reaction_with_livechat",
        )
