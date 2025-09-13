# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, tests
from odoo.addons.im_livechat.tests.chatbot_common import ChatbotCase
from odoo.addons.website_livechat.tests.common import TestLivechatCommon as TestWebsiteLivechatCommon
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


@tests.tagged('post_install', '-at_install')
class TestLivechatChatbotUI(TestImLivechatCommon, TestWebsiteLivechatCommon, ChatbotCase):
    def setUp(self):
        super().setUp()
        self.env['im_livechat.channel'].search([
            ('id', '!=', self.livechat_channel.id)
        ]).unlink()  # delete other channels to avoid them messing with the URL rules

        self.livechat_channel.write({
            'is_published': True,
            'rule_ids': [(5, 0), (0, 0, {
                'action': 'auto_popup',
                'regex_url': '/',
                'chatbot_script_id': self.chatbot_script.id,
            })]
        })

        self.env.ref('website.default_website').channel_id = self.livechat_channel.id

    def test_complete_chatbot_flow_ui(self):
        self.start_tour('/', 'website_livechat_chatbot_flow_tour', step_delay=100)

        operator = self.chatbot_script.operator_partner_id
        livechat_discuss_channel = self.env['discuss.channel'].search([
            ('livechat_channel_id', '=', self.livechat_channel.id),
            ('livechat_operator_id', '=', operator.id),
            ('message_ids', '!=', False),
        ])

        self.assertTrue(bool(livechat_discuss_channel))
        self.assertEqual(len(livechat_discuss_channel), 1)

        conversation_messages = livechat_discuss_channel.message_ids.sorted('id')

        expected_messages = [
            ("Hello! I'm a bot!", operator, False),
            ("I help lost visitors find their way.", operator, False),
            # next message would normally have 'self.step_dispatch_buy_software' as answer
            # but it's wiped when restarting the script
            ("How can I help you?", operator, False),
            ("I want to buy the software", False, False),
            ("Can you give us your email please?", operator, False),
            ("No, you won't get my email!", False, False),
            ("'No, you won't get my email!' does not look like a valid email. Can you please try again?", operator, False),
            ("okfine@fakeemail.com", False, False),
            ("Your email is validated, thank you!", operator, False),
            ("Would you mind providing your website address?", operator, False),
            ("https://www.fakeaddress.com", False, False),
            ("Great, do you want to leave any feedback for us to improve?", operator, False),
            ("Yes, actually, I'm glad you asked!", False, False),
            ("I think it's outrageous that you ask for all my personal information!", False, False),
            ("I will be sure to take this to your manager!", False, False),
            ("Ok bye!", operator, False),
            ("Restarting conversation...", operator, False),
            ("Hello! I'm a bot!", operator, False),
            ("I help lost visitors find their way.", operator, False),
            ("How can I help you?", operator, self.step_dispatch_pricing),
            ("Pricing Question", False, False),
            ("For any pricing question, feel free ton contact us at pricing@mycompany.com", operator, False),
            ("We will reach back to you as soon as we can!", operator, False),
            ("Would you mind providing your website address?", operator, False),
            ("no", False, False),
            ("Great, do you want to leave any feedback for us to improve?", operator, False),
            ("no, nothing so say", False, False),
            ("Ok bye!", operator, False),
        ]

        self.assertEqual(len(conversation_messages), len(expected_messages))

        # check that the whole conversation is correctly saved
        # including welcome steps: see chatbot.script#_post_welcome_steps
        for conversation_message, expected_message in zip(conversation_messages, expected_messages):
            [body, operator, user_script_answer_id] = expected_message

            self.assertIn(body, conversation_message.body)

            if operator:
                self.assertEqual(conversation_message.author_id, operator)
            else:
                self.assertNotEqual(conversation_message.author_id, operator)

            if user_script_answer_id:
                self.assertEqual(
                    user_script_answer_id,
                    self.env['chatbot.message'].search([
                        ('mail_message_id', '=', conversation_message.id)
                    ], limit=1).user_script_answer_id
                )

    def test_chatbot_available_after_reload(self):
        self.start_tour("/", "website_livechat_chatbot_after_reload_tour", step_delay=100)

    def test_chatbot_redirect(self):
        chatbot_redirect_script = self.env["chatbot.script"].create(
            {"title": "Redirection Bot"}
        )
        question_step, _ = tuple(
            self.env["chatbot.script.step"].create([
                {
                    "chatbot_script_id": chatbot_redirect_script.id,
                    "message": "Hello, were do you want to go?",
                    "step_type": "question_selection",
                },
                {
                    "chatbot_script_id": chatbot_redirect_script.id,
                    "message": "Tadam, we are on the page you asked for!",
                    "step_type": "text",
                }
            ])
        )
        self.env["chatbot.script.answer"].create([
            {
                "name": "Go to the #chatbot-redirect anchor",
                "redirect_link": "#chatbot-redirect",
                "script_step_id": question_step.id,
            },
            {
                "name": "Go to the /chatbot-redirect page",
                "redirect_link": "/chatbot-redirect",
                "script_step_id": question_step.id,
            },
        ])
        livechat_channel = self.env["im_livechat.channel"].create({
            'name': 'Redirection Channel',
            'rule_ids': [Command.create({
                'regex_url': '/contactus',
                'chatbot_script_id': chatbot_redirect_script.id,
            })]
        })
        default_website = self.env.ref("website.default_website")
        default_website.channel_id = livechat_channel.id
        self.env.ref("website.default_website").channel_id = livechat_channel.id
        self.start_tour("/contactus", "website_livechat.chatbot_redirect")

    def test_chatbot_fw_operator_matching_lang(self):
        fr_op = self._create_operator(lang_code="fr_FR")
        en_op = self._create_operator(lang_code="en_US")
        self.env.ref("website.default_website").language_ids = self.env["res.lang"].search(
            [["code", "in", ["fr_FR", "en_US"]]]
        )
        self.livechat_channel.user_ids = fr_op + en_op
        self.env["discuss.channel"].search([("livechat_channel_id", "=", self.livechat_channel.id)]).unlink()
        self.start_tour("/fr", "chatbot_fw_operator_matching_lang")
        channel = self.livechat_channel.channel_ids[0]
        self.assertIn(channel.channel_member_ids.partner_id.user_ids, fr_op)
        self.assertNotIn(channel.channel_member_ids.partner_id.user_ids, en_op)
        self.env["discuss.channel"].search([("livechat_channel_id", "=", self.livechat_channel.id)]).unlink()
        self.start_tour("/en", "chatbot_fw_operator_matching_lang")
        channel = self.livechat_channel.channel_ids[0]
        self.assertIn(channel.channel_member_ids.partner_id.user_ids, en_op)
        self.assertNotIn(channel.channel_member_ids.partner_id.user_ids, fr_op)

    def test_chatbot_restore_state(self):
        chatbot_state_restore_script = self.env["chatbot.script"].create(
            {"title": "Restore state Bot"}
        )
        self.env["chatbot.script.step"].create([
            {
                "chatbot_script_id": chatbot_state_restore_script.id,
                "step_type": "text",
                "message": "How can I help you?",
                "sequence": 2,  # Swapped sequence
            },
            {
                "chatbot_script_id": chatbot_state_restore_script.id,
                "step_type": "text",
                "message": "Hello! I'm a bot for restoration test!",
                "sequence": 1,  # Swapped sequence
            },
        ])
        livechat_channel = self.env["im_livechat.channel"].create({
            "name": "State restore Channel",
            "rule_ids": [Command.create({
                'regex_url': '/contactus',
                "chatbot_script_id": chatbot_state_restore_script.id,
            })]
        })
        default_website = self.env.ref("website.default_website")
        default_website.channel_id = livechat_channel.id
        self.env.ref("website.default_website").channel_id = livechat_channel.id
        self.start_tour("/contactus", "website_livechat.chatbot_restore_state_tour")
