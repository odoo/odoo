# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class ChatbotCase(common.HttpCase):

    @classmethod
    def setUpClass(cls):
        super(ChatbotCase, cls).setUpClass()
        cls.maxDiff = None

        cls.chatbot_script = cls.env['chatbot.script'].create({
            'title': 'Testing Bot',
        })

        ChatbotScriptStep = cls.env['chatbot.script.step'].sudo()

        [
            cls.step_hello,
            cls.step_welcome,
            cls.step_dispatch,
        ] = ChatbotScriptStep.create([{
            'step_type': 'text',
            'message': "Hello! I'm a bot!",
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'text',
            'message': "I help lost visitors find their way.",
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'question_selection',
            'message': "How can I help you?",
            'chatbot_script_id': cls.chatbot_script.id,
        }])

        [
            cls.step_dispatch_buy_software,
            cls.step_dispatch_pricing,
            cls.step_dispatch_operator,
            cls.step_dispatch_documentation,
        ] = cls.env['chatbot.script.answer'].sudo().create([{
            'name': 'I\'d like to buy the software',
            'script_step_id': cls.step_dispatch.id,
        }, {
            'name': 'Pricing Question',
            'script_step_id': cls.step_dispatch.id,
        }, {
            'name': "I want to speak with an operator",
            'script_step_id': cls.step_dispatch.id,
        }, {
            'name': "Other & Documentation",
            'script_step_id': cls.step_dispatch.id,
        }])

        [
            cls.step_pricing_contact_us,
            cls.step_email,
            cls.step_email_validated,
            cls.step_forward_operator,
            cls.step_no_one_available,
            cls.step_no_operator_dispatch,
            cls.step_documentation_validated,
        ] = ChatbotScriptStep.create([{
            'step_type': 'text',
            'message': 'For any pricing question, feel free ton contact us at pricing@mycompany.com',
            'triggering_answer_ids': [(4, cls.step_dispatch_pricing.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'question_email',
            'message': 'Can you give us your email please?',
            'triggering_answer_ids': [(4, cls.step_dispatch_buy_software.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'text',
            'message': 'Your email is validated, thank you!',
            'triggering_answer_ids': [(4, cls.step_dispatch_buy_software.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'forward_operator',
            'message': 'I will transfer you to a human.',
            'triggering_answer_ids': [(4, cls.step_dispatch_operator.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'text',
            'message': 'Sorry, you will have to stay with me for a while',
            'triggering_answer_ids': [(4, cls.step_dispatch_operator.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'question_selection',
            'message': 'So... What can I do to help you?',
            'triggering_answer_ids': [(4, cls.step_dispatch_operator.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'text',
            'message': 'Please find documentation at https://www.odoo.com/documentation/latest/',
            'triggering_answer_ids': [(4, cls.step_dispatch_documentation.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }])

        cls.step_no_operator_just_leaving = cls.env['chatbot.script.answer'].sudo().create({
            'name': 'I will be leaving then',
            'script_step_id': cls.step_no_operator_dispatch.id,
        })

        [
            cls.step_just_leaving,
            cls.step_pricing_thank_you,
            cls.step_ask_website,
            cls.step_ask_feedback,
            cls.step_goodbye,
        ] = ChatbotScriptStep.create([{
            'step_type': 'text',
            'message': "Ok, I'm sorry I was not able to help you",
            'triggering_answer_ids': [(4, cls.step_no_operator_just_leaving.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'text',
            'message': 'We will reach back to you as soon as we can!',
            'triggering_answer_ids': [(4, cls.step_dispatch_pricing.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'free_input_single',
            'message': 'Would you mind providing your website address?',
            'sequence': 97,  # makes it easier for other modules to add steps before this one
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'free_input_multi',
            'message': 'Great, do you want to leave any feedback for us to improve?',
            'sequence': 98,  # makes it easier for other modules to add steps before this one
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'text',
            'message': "Ok bye!",
            'sequence': 99,  # makes it easier for other modules to add steps before this one
            'chatbot_script_id': cls.chatbot_script.id,
        }])

        cls.livechat_channel = cls.env['im_livechat.channel'].create({
            'name': 'Test Channel',
            'rule_ids': [(0, 0, {
                'chatbot_script_id': cls.chatbot_script.id,
            })]
        })

    def _post_answer_and_trigger_next_step(
        self, discuss_channel, body=None, email=None, chatbot_script_answer=None
    ):
        data = self.make_jsonrpc_request(
            "/mail/message/post",
            {
                "thread_model": "discuss.channel",
                "thread_id": discuss_channel.id,
                "post_data": {
                    "body": body or email or chatbot_script_answer.name,
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_comment",
                },
            },
        )
        if email:
            self.make_jsonrpc_request(
                "/chatbot/step/validate_email", {"channel_id": discuss_channel.id}
            )
        if chatbot_script_answer:
            message = self.env["mail.message"].browse(data["message_id"])
            self.make_jsonrpc_request(
                "/chatbot/answer/save",
                {
                    "channel_id": discuss_channel.id,
                    "message_id": message.id,
                    "selected_answer_id": chatbot_script_answer.id,
                },
            )
        self.make_jsonrpc_request("/chatbot/step/trigger", {"channel_id": discuss_channel.id})
