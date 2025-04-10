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

    def _check_complete_chatbot_flow_result(self):
        operator = self.chatbot_script.operator_partner_id
        livechat_discuss_channel = self.env['discuss.channel'].search([
            ('livechat_channel_id', '=', self.livechat_channel.id),
            ('livechat_operator_id', '=', operator.id),
            ('message_ids', '!=', False),
        ])
        self.assertTrue(bool(livechat_discuss_channel))
        self.assertEqual(len(livechat_discuss_channel), 1)

        conversation_messages = livechat_discuss_channel.message_ids.sorted('id')
        operator_member = livechat_discuss_channel.channel_member_ids.filtered(
            lambda m: m.partner_id == self.operator.partner_id
        )

        expected_messages = [
            ("Hello! I'm a bot!", operator, False),
            ("I help lost visitors find their way.", operator, False),
            # next message would normally have 'self.step_dispatch_buy_software' as answer
            # but it's wiped when restarting the script
            ("How can I help you?", operator, False),
            ("I\'d like to buy the software", False, False),
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
            ("How can I help you?", operator, False),
            ("Pricing Question", False, False),
            ("For any pricing question, feel free ton contact us at pricing@mycompany.com", operator, False),
            ("We will reach back to you as soon as we can!", operator, False),
            ("Would you mind providing your website address?", operator, False),
            ("no", False, False),
            ("Great, do you want to leave any feedback for us to improve?", operator, False),
            ("no, nothing so say", False, False),
            ("Ok bye!", operator, False),
            ("Restarting conversation...", operator, False),
            ("Hello! I'm a bot!", operator, False),
            ("I help lost visitors find their way.", operator, False),
            ("How can I help you?", operator, self.step_dispatch_operator),
            ("I want to speak with an operator", False, False),
            ("I will transfer you to a human", operator, False),
            (
                'invited <a href="#" data-oe-model="res.partner" data-oe-id="'
                f'{operator_member.partner_id.id}">@Operator Michel</a> to the channel',
                self.chatbot_script.operator_partner_id,
                False,
            ),
        ]

        self.assertEqual(len(conversation_messages), len(expected_messages))
        # "invited" notification is not taken into account in unread counter contribution.
        self.assertEqual(len(conversation_messages) - 1, operator_member.message_unread_counter)

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

    def test_complete_chatbot_flow_ui(self):
        tests.new_test_user(self.env, login="portal_user", groups="base.group_portal")
        operator = self.chatbot_script.operator_partner_id
        self.start_tour('/', 'website_livechat_chatbot_flow_tour')
        self._check_complete_chatbot_flow_result()
        self.env['discuss.channel'].search([
            ('livechat_channel_id', '=', self.livechat_channel.id),
            ('livechat_operator_id', '=', operator.id),
        ]).unlink()
        self.start_tour('/', 'website_livechat_chatbot_flow_tour', login="portal_user")
        self._check_complete_chatbot_flow_result()

    def test_chatbot_available_after_reload(self):
        self.start_tour("/", "website_livechat_chatbot_after_reload_tour")

    def test_chatbot_test_page_tour(self):
        bob_operator = tests.new_test_user(self.env, login="bob_user", groups="im_livechat.im_livechat_group_user,base.group_user")
        self.livechat_channel.user_ids += bob_operator
        test_page_url = f"/chatbot/{'-'.join(self.chatbot_script.title.split(' '))}-{self.chatbot_script.id}/test"
        self.start_tour(test_page_url, "website_livechat_chatbot_test_page_tour", login="bob_user")

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

    def test_chatbot_trigger_selection(self):
        chatbot_trigger_selection = self.env["chatbot.script"].create(
            {"title": "Trigger question selection bot"}
        )
        question_1, question_2 = tuple(
            self.env["chatbot.script.step"].create([
                {
                    "chatbot_script_id": chatbot_trigger_selection.id,
                    "message": "Hello, here is a first question?",
                    "step_type": "question_selection",
                },
                {
                    "chatbot_script_id": chatbot_trigger_selection.id,
                    "message": "Hello, here is a second question?",
                    "step_type": "question_selection",
                },
            ])
        )
        self.env["chatbot.script.answer"].create([
            {
                "name": "Yes to first question",
                "script_step_id": question_1.id,
            },
            {
                "name": "No to second question",
                "script_step_id": question_2.id,
            },
        ])
        livechat_channel = self.env["im_livechat.channel"].create({
            'name': 'Redirection Channel',
            'rule_ids': [Command.create({
                'regex_url': '/contactus',
                'chatbot_script_id': chatbot_trigger_selection.id,
            })]
        })
        default_website = self.env.ref("website.default_website")
        default_website.channel_id = livechat_channel.id
        self.env.ref("website.default_website").channel_id = livechat_channel.id
        self.start_tour("/contactus", "website_livechat.chatbot_trigger_selection")

    def test_chatbot_fw_operator_matching_lang(self):
        fr_op = self._create_operator(lang_code="fr_FR")
        en_op = self._create_operator(lang_code="en_US")
        self.env.ref("website.default_website").language_ids = self.env["res.lang"].search(
            [("code", "in", ("fr_FR", "en_US"))]
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

    def test_question_selection_overlapping_answers(self):
        chatbot_script = self.env["chatbot.script"].create({"title": "Question selection bot"})
        question_1 = self.env["chatbot.script.step"].create(
            [
                {
                    "chatbot_script_id": chatbot_script.id,
                    "message": "Choose an option",
                    "step_type": "question_selection",
                },
            ]
        )
        not_x_answer = self.env["chatbot.script.answer"].create({
            "name": "not X",
            "script_step_id": question_1.id,
        })
        x_answer = self.env["chatbot.script.answer"].create({
            "name": "X",
            "script_step_id": question_1.id,
        })
        maybe_x_answer = self.env["chatbot.script.answer"].create({
            "name": "Maybe X",
            "script_step_id": question_1.id,
        })
        self.env["chatbot.script.step"].create(
            [
                {
                    "chatbot_script_id": chatbot_script.id,
                    "step_type": "text",
                    "triggering_answer_ids": [not_x_answer.id],
                    "message": "You selected not X",
                },
                {
                    "chatbot_script_id": chatbot_script.id,
                    "step_type": "text",
                    "triggering_answer_ids": [x_answer.id],
                    "message": "You selected X",
                },
                {
                    "chatbot_script_id": chatbot_script.id,
                    "step_type": "text",
                    "triggering_answer_ids": [maybe_x_answer.id],
                    "message": "You selected maybe X",
                },
            ]
        )
        self.livechat_channel.rule_ids = self.env["im_livechat.channel.rule"].create(
            [
                {
                    "channel_id": self.livechat_channel.id,
                    "chatbot_script_id": chatbot_script.id,
                    "regex_url": "/",
                },
            ]
        )
        self.start_tour("/", "website_livechat.question_selection_overlapping_answers")
