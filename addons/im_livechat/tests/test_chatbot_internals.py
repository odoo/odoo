# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.im_livechat.tests import chatbot_common
from odoo.tests.common import JsonRpcException, tagged


@tagged("post_install", "-at_install")
class ChatbotCase(chatbot_common.ChatbotCase):

    def test_chatbot_duplicate(self):
        """ In this test we make sure that 'triggering_answer_ids' are correctly duplicated and
        reference the answers from the copied script steps.
        See chatbot.script#copy for more details. """

        chatbot_copy = self.chatbot_script.copy()

        step_pricing_contact_us_copy = chatbot_copy.script_step_ids.filtered(
            lambda step: 'For any pricing question, feel free ton contact us at pricing@mycompany.com' in step.message)

        self.assertNotEqual(step_pricing_contact_us_copy, self.step_pricing_contact_us)
        self.assertEqual(len(step_pricing_contact_us_copy.triggering_answer_ids), 1)
        self.assertEqual(step_pricing_contact_us_copy.triggering_answer_ids.name, 'Pricing Question')
        self.assertNotEqual(step_pricing_contact_us_copy.triggering_answer_ids, self.step_dispatch_pricing)

        step_email_copy = chatbot_copy.script_step_ids.filtered(
            lambda step: 'Can you give us your email please' in step.message)

        self.assertNotEqual(step_email_copy, self.step_email)
        self.assertEqual(len(step_email_copy.triggering_answer_ids), 1)
        self.assertEqual(step_email_copy.triggering_answer_ids.name, 'I want to buy the software')
        self.assertNotEqual(step_email_copy.triggering_answer_ids, self.step_dispatch_buy_software)

    def test_chatbot_is_forward_operator_child(self):
        self.assertEqual([step.is_forward_operator_child for step in self.chatbot_script.script_step_ids],
                         [False, False, False, False, False, False, False, True, True, False, True, False, False, False, False],
                         "Steps 'step_no_one_available', 'step_no_operator_dispatch', 'step_just_leaving'"
                         "should be flagged as forward operator child.")

        self.step_no_operator_dispatch.write({'triggering_answer_ids': [(6, 0, [self.step_dispatch_pricing.id])]})
        self.chatbot_script.script_step_ids.invalidate_recordset(['is_forward_operator_child'])

        self.assertEqual([step.is_forward_operator_child for step in self.chatbot_script.script_step_ids],
                         [False, False, False, False, False, False, False, True, False, False, False, False, False, False, False],
                         "Only step 'step_no_one_available' should be flagged as forward operator child.")

    def test_chatbot_steps(self):
        data = self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'Test Visitor',
            'chatbot_script_id': self.chatbot_script.id,
            'channel_id': self.livechat_channel.id,
        })
        discuss_channel = self.env["discuss.channel"].browse(data["discuss.channel"][0]["id"])

        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_dispatch)

        self._post_answer_and_trigger_next_step(
            discuss_channel, chatbot_script_answer=self.step_dispatch_buy_software
        )
        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_email)

        with self.assertRaises(JsonRpcException, msg='odoo.exceptions.ValidationError'):
            self._post_answer_and_trigger_next_step(discuss_channel, email="test")

        self._post_answer_and_trigger_next_step(discuss_channel, email="test@example.com")
        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_email_validated)

    def test_chatbot_steps_sequence(self):
        """ Ensure sequence is correct when creating chatbots and adding steps to an existing one.
        See chatbot.script.step#create for more details. """

        chatbot_1, chatbot_2 = self.env['chatbot.script'].create([{
            'title': 'Chatbot 1',
            'script_step_ids': [
                (0, 0, {'step_type': 'text', 'message': '1'}),
                (0, 0, {'step_type': 'text', 'message': '2'}),
                (0, 0, {'step_type': 'text', 'message': '3'}),
                (0, 0, {'step_type': 'text', 'message': '4'}),
                (0, 0, {'step_type': 'text', 'message': '5'}),
            ]
        }, {
            'title': 'Chatbot 2',
            'script_step_ids': [
                (0, 0, {'step_type': 'text', 'message': '1'}),
                (0, 0, {'step_type': 'text', 'message': '2'}),
                (0, 0, {'step_type': 'text', 'message': '3'}),
            ]
        }])

        self.assertEqual([0, 1, 2, 3, 4], chatbot_1.script_step_ids.mapped('sequence'))
        self.assertEqual([0, 1, 2], chatbot_2.script_step_ids.mapped('sequence'))

        chatbot_1.write({'script_step_ids': [
            (0, 0, {'step_type': 'text', 'message': '6'}),
            (0, 0, {'step_type': 'text', 'message': '7'}),
        ]})
        self.assertEqual([0, 1, 2, 3, 4, 5, 6], chatbot_1.script_step_ids.mapped('sequence'))

    def test_chatbot_welcome_steps(self):
        """ see '_get_welcome_steps' for more details. """

        welcome_steps = self.chatbot_script._get_welcome_steps()
        self.assertEqual(len(welcome_steps), 3)
        self.assertEqual(welcome_steps, self.chatbot_script.script_step_ids[:3])

        self.chatbot_script.script_step_ids[:2].unlink()
        welcome_steps = self.chatbot_script._get_welcome_steps()
        self.assertEqual(len(welcome_steps), 1)
        self.assertEqual(welcome_steps, self.chatbot_script.script_step_ids[0])

    def test_chatbot_not_invited_to_rtc_calls(self):
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "anonymous_name": "Test Visitor",
                "channel_id": self.livechat_channel.id,
                "chatbot_script_id": self.chatbot_script.id,
            },
        )
        discuss_channel = (
            self.env["discuss.channel"].sudo().browse(data["discuss.channel"][0]["id"])
        )
        self.assertEqual(discuss_channel.livechat_operator_id, self.chatbot_script.operator_partner_id)
        discuss_channel.add_members(partner_ids=self.env.user.partner_id.ids)
        self_member = discuss_channel.channel_member_ids.filtered(lambda m: m.is_self)
        bot_member = discuss_channel.channel_member_ids.filtered(
            lambda m: m.partner_id == self.chatbot_script.operator_partner_id
        )
        guest_member = discuss_channel.channel_member_ids.filtered(lambda m: bool(m.guest_id))
        self_member._rtc_join_call()
        self.assertTrue(guest_member.rtc_inviting_session_id)
        self.assertFalse(bot_member.rtc_inviting_session_id)

    def test_forward_to_specific_operator(self):
        """Test _process_step_forward_operator takes into account the given users as candidates."""
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "anonymous_name": "Test Visitor",
                "channel_id": self.livechat_channel.id,
                "chatbot_script_id": self.chatbot_script.id,
            },
        )
        discuss_channel = (
            self.env["discuss.channel"].sudo().browse(data["discuss.channel"][0]["id"])
        )
        self.step_forward_operator._process_step_forward_operator(discuss_channel)
        self.assertEqual(
            discuss_channel.livechat_operator_id, self.chatbot_script.operator_partner_id
        )
        self.step_forward_operator._process_step_forward_operator(
            discuss_channel, users=self.user_employee
        )
        self.assertEqual(discuss_channel.livechat_operator_id, self.partner_employee)
