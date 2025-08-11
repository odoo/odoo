# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.im_livechat.tests import chatbot_common
from odoo.tests.common import JsonRpcException, new_test_user, tagged
from odoo.tools.misc import mute_logger
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store


@tagged("post_install", "-at_install")
class ChatbotCase(MailCommon, chatbot_common.ChatbotCase):

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
        self.assertEqual(step_email_copy.triggering_answer_ids.name, 'I\'d like to buy the software')
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
            'chatbot_script_id': self.chatbot_script.id,
            'channel_id': self.livechat_channel.id,
        })
        discuss_channel = self.env["discuss.channel"].browse(data["channel_id"])

        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_dispatch)

        self._post_answer_and_trigger_next_step(
            discuss_channel, chatbot_script_answer=self.step_dispatch_buy_software
        )
        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_email)

        with self.assertRaises(JsonRpcException, msg='odoo.exceptions.ValidationError'), mute_logger("odoo.http"):
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
                "channel_id": self.livechat_channel.id,
                "chatbot_script_id": self.chatbot_script.id,
            },
        )
        discuss_channel = (
            self.env["discuss.channel"].sudo().browse(data["channel_id"])
        )
        self.assertEqual(discuss_channel.livechat_operator_id, self.chatbot_script.operator_partner_id)
        discuss_channel._add_members(users=self.env.user)
        self_member = discuss_channel.channel_member_ids.filtered(lambda m: m.is_self)
        bot_member = discuss_channel.channel_member_ids.filtered(
            lambda m: m.partner_id == self.chatbot_script.operator_partner_id
        )
        guest_member = discuss_channel.channel_member_ids.filtered(lambda m: bool(m.guest_id))
        self_member._rtc_join_call()
        self.assertTrue(guest_member.rtc_inviting_session_id)
        self.assertFalse(bot_member.rtc_inviting_session_id)

    @freeze_time("2020-03-22 10:42:06")
    def test_forward_to_specific_operator(self):
        """Test _forward_operator takes into account the given users as candidates."""
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "chatbot_script_id": self.chatbot_script.id,
            },
        )
        discuss_channel = (
            self.env["discuss.channel"].sudo().browse(data["channel_id"])
        )
        discuss_channel._forward_human_operator(self.step_forward_operator)
        self.assertEqual(
            discuss_channel.livechat_operator_id, self.chatbot_script.operator_partner_id
        )
        self.assertEqual(discuss_channel.name, "Testing Bot")

        member_bot = discuss_channel.channel_member_ids.filtered(
            lambda m: m.partner_id == self.chatbot_script.operator_partner_id
        )
        member_bot_data = {
            "create_date": fields.Datetime.to_string(member_bot.create_date),
            "fetched_message_id": False,
            "id": member_bot.id,
            "livechat_member_type": "bot",
            "last_seen_dt": False,
            "partner_id": member_bot.partner_id.id,
            "seen_message_id": False,
            "channel_id": {"id": discuss_channel.id, "model": "discuss.channel"},
        }

        def get_forward_op_bus_params():
            messages = self.env["mail.message"].search([], order="id desc", limit=3)
            # only data relevant to the test are asserted for simplicity
            transfer_message_data = Store(bus_channel=discuss_channel).add(messages[1]).get_result()
            transfer_message_data["mail.message"][0].update(
                {
                    "author_id": self.chatbot_script.operator_partner_id.id,
                    "body": ["markup", "<p>I will transfer you to a human.</p>"],
                    # thread not renamed yet at this step
                    "default_subject": "Testing Bot",
                    "record_name": "Testing Bot",
                }
            )
            transfer_message_data["mail.thread"][0]["display_name"] = "Testing Bot"
            joined_message_data = Store(bus_channel=discuss_channel).add(messages[0]).get_result()
            joined_message_data["mail.message"][0].update(
                {
                    "author_id": self.chatbot_script.operator_partner_id.id,
                    "body": [
                        "markup",
                        (
                            '<div class="o_mail_notification" data-oe-type="channel-joined">invited <a href="#" data-oe-model="res.partner" data-oe-id="'
                            f'{self.partner_employee.id}">@Ernest Employee</a> to the channel</div>'
                        ),
                    ],
                    # thread not renamed yet at this step
                    "default_subject": "Testing Bot",
                    "record_name": "Testing Bot",
                }
            )
            joined_message_data["mail.thread"][0]["display_name"] = "Testing Bot"
            member_emp = discuss_channel.channel_member_ids.filtered(
                lambda m: m.partner_id == self.partner_employee
            )
            # data in-between join and leave
            channel_data_join = (
                Store(bus_channel=member_emp._bus_channel()).add(discuss_channel).get_result()
            )
            channel_data_join["discuss.channel"][0]["invited_member_ids"] = [["ADD", []]]
            channel_data_join["discuss.channel"][0]["rtc_session_ids"] = [["ADD", []]]
            channel_data_join["discuss.channel"][0]["livechat_outcome"] = "no_agent"
            channel_data_join["discuss.channel"][0]["chatbot"]["currentStep"]["message"] = messages[1].id
            channel_data_join["discuss.channel"][0]["chatbot"]["steps"][0]["message"] = messages[1].id
            channel_data_join["discuss.channel"][0]["livechat_operator_id"] = self.chatbot_script.operator_partner_id.id
            channel_data_join["discuss.channel"][0]["member_count"] = 3
            channel_data_join["discuss.channel"][0]["name"] = "Testing Bot"
            channel_data_join["discuss.channel"][0]["livechat_with_ai_agent"] = False
            channel_data_join["discuss.channel.member"].insert(0, member_bot_data)
            channel_data_join["discuss.channel.member"][2]["fetched_message_id"] = False
            channel_data_join["discuss.channel.member"][2]["last_seen_dt"] = False
            channel_data_join["discuss.channel.member"][2]["seen_message_id"] = False
            channel_data_join["discuss.channel.member"][2]["unpin_dt"] = False
            del channel_data_join["res.partner"][1]
            channel_data_join["res.partner"].insert(
                0,
                {
                    "active": False,
                    "avatar_128_access_token": self.chatbot_script.operator_partner_id._get_avatar_128_access_token(),
                    "country_id": False,
                    "id": self.chatbot_script.operator_partner_id.id,
                    "im_status": "im_partner",
                    "im_status_access_token": self.chatbot_script.operator_partner_id._get_im_status_access_token(),
                    "is_public": False,
                    "name": "Testing Bot",
                    "user_livechat_username": False,
                    "write_date": fields.Datetime.to_string(
                        self.chatbot_script.operator_partner_id.write_date
                    ),
                },
            )
            channel_data = Store().add(discuss_channel).get_result()
            channel_data["discuss.channel"][0]["message_needaction_counter_bus_id"] = 0
            channel_data_emp = Store().add(discuss_channel.with_user(self.user_employee)).get_result()
            channel_data_emp["discuss.channel"][0]["message_needaction_counter_bus_id"] = 0
            channel_data_emp["discuss.channel"][0]["livechat_with_ai_agent"] = False
            channel_data_emp["discuss.channel.member"][1]["message_unread_counter_bus_id"] = 0
            channel_data = Store().add(discuss_channel).get_result()
            channel_data["discuss.channel"][0]["message_needaction_counter_bus_id"] = 0
            channel_data["discuss.channel"][0]["livechat_with_ai_agent"] = False
            self._filter_channels_fields(
                channel_data_join['discuss.channel'][0],
                channel_data_emp['discuss.channel'][0],
                channel_data['discuss.channel'][0],
            )
            channels, message_items = (
                [
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "res.partner", self.partner_employee.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "res.partner", self.partner_employee.id),
                    (self.cr.dbname, "res.partner", self.env.user.partner_id.id),
                ],
                [
                    {
                        "type": "discuss.channel/new_message",
                        "payload": {
                            "data": transfer_message_data,
                            "id": discuss_channel.id,
                        },
                    },
                    {
                        "type": "discuss.channel/joined",
                        "payload": {
                            "channel_id": discuss_channel.id,
                            "data": channel_data_join,
                            "invited_by_user_id": self.env.user.id,
                        },
                    },
                    {
                        "type": "discuss.channel/new_message",
                        "payload": {
                            "data": joined_message_data,
                            "id": discuss_channel.id,
                        },
                    },
                    {
                        "type": "mail.record/insert",
                        "payload": {
                            "discuss.channel": [{"id": discuss_channel.id, "member_count": 3}],
                            "discuss.channel.member": [
                                {
                                    "create_date": fields.Datetime.to_string(
                                        member_emp.create_date
                                    ),
                                    "fetched_message_id": False,
                                    "id": member_emp.id,
                                    "livechat_member_type": "agent",
                                    "last_seen_dt": fields.Datetime.to_string(
                                        member_emp.last_seen_dt
                                    ),
                                    "partner_id": self.partner_employee.id,
                                    "seen_message_id": False,
                                    "channel_id": {
                                        "id": discuss_channel.id,
                                        "model": "discuss.channel",
                                    },
                                }
                            ],
                            "res.country": [
                                {"code": "BE", "id": self.env.ref("base.be").id, "name": "Belgium"}
                            ],
                            "res.partner": self._filter_partners_fields(
                                {
                                    "active": True,
                                    "avatar_128_access_token": self.partner_employee._get_avatar_128_access_token(),
                                    "country_id": self.env.ref("base.be").id,
                                    "id": self.partner_employee.id,
                                    "im_status": "offline",
                                    "im_status_access_token": self.partner_employee._get_im_status_access_token(),
                                    "is_public": False,
                                    "name": "Ernest Employee",
                                    "user_livechat_username": False,
                                    "write_date": fields.Datetime.to_string(
                                        self.partner_employee.write_date
                                    ),
                                }
                            ),
                        },
                    },
                    {
                        "type": "mail.record/insert",
                        "payload": {
                            "discuss.channel": [
                                {
                                    "channel_member_ids": [["DELETE", [member_bot.id]]],
                                    "id": discuss_channel.id,
                                    "member_count": 2,
                                }
                            ]
                        },
                    },
                    {
                        "type": "mail.record/insert",
                        "payload": {
                            "discuss.channel": [
                                {
                                    "id": discuss_channel.id,
                                    "livechat_operator_id": self.partner_employee.id,
                                    "name": "OdooBot Ernest Employee",
                                },
                            ],
                            "res.partner": self._filter_partners_fields(
                                {
                                    "avatar_128_access_token": self.partner_employee._get_avatar_128_access_token(),
                                    "id": self.partner_employee.id,
                                    "name": "Ernest Employee",
                                    "user_livechat_username": False,
                                    "write_date": fields.Datetime.to_string(
                                        self.partner_employee.write_date
                                    ),
                                    **({
                                        "im_status": "offline",
                                        "im_status_access_token": self.partner_employee._get_im_status_access_token()
                                    } if "ai.agent" in self.env else {})
                                }
                            ),
                        },
                    },
                    {"type": "mail.record/insert", "payload": channel_data_emp},
                    {"type": "mail.record/insert", "payload": channel_data},
                ],
            )

            return (channels, message_items)
        with self.assertBus(get_params=get_forward_op_bus_params):
            discuss_channel._forward_human_operator(self.step_forward_operator, users=self.user_employee)
        self.assertEqual(discuss_channel.name, "OdooBot Ernest Employee")
        self.assertEqual(discuss_channel.livechat_operator_id, self.partner_employee)
        self.assertEqual(discuss_channel.livechat_outcome, "no_answer")
        self.assertTrue(
            discuss_channel.channel_member_ids.filtered(
                lambda m: m.partner_id == self.partner_employee
                and m.livechat_member_type == "agent"
            )
        )

    def test_chatbot_multiple_rules_on_same_url(self):
        bob_user = new_test_user(
            self.env, login="bob_user", groups="im_livechat.im_livechat_group_user,base.group_user"
        )
        chatbot_no_operator = self.env["chatbot.script"].create(
            {
                "title": "Chatbot operators not available",
                "script_step_ids": [
                    Command.create(
                        {
                            "step_type": "text",
                            "message": "I'm shown because there is no operator available",
                        }
                    )
                ],
            }
        )
        chatbot_operator = self.env["chatbot.script"].create(
            {
                "title": "Chatbot operators available",
                "script_step_ids": [
                    Command.create(
                        {
                            "step_type": "text",
                            "message": "I'm shown because there is an operator available",
                        }
                    )
                ],
            }
        )
        self.livechat_channel.user_ids += bob_user
        self.livechat_channel.rule_ids = self.env["im_livechat.channel.rule"].create(
            [
                {
                    "channel_id": self.livechat_channel.id,
                    "chatbot_script_id": chatbot_no_operator.id,
                    "chatbot_enabled_condition": "only_if_no_operator",
                    "regex_url": "/",
                    "sequence": 1,
                },
                {
                    "channel_id": self.livechat_channel.id,
                    "chatbot_script_id": chatbot_operator.id,
                    "regex_url": "/",
                    "sequence": 2,
                },
            ]
        )
        self.assertFalse(self.livechat_channel.available_operator_ids)
        self.assertEqual(
            self.env["im_livechat.channel.rule"]
            .match_rule(self.livechat_channel.id, "/")
            .chatbot_script_id,
            chatbot_no_operator,
        )
        self.env["mail.presence"]._update_presence(bob_user)
        # Force the recomputation of `available_operator_ids` after bob becomes online
        self.livechat_channel.invalidate_recordset(["available_operator_ids"])
        self.assertTrue(self.livechat_channel.available_operator_ids)
        self.assertEqual(
            self.env["im_livechat.channel.rule"]
            .match_rule(self.livechat_channel.id, "/")
            .chatbot_script_id,
            chatbot_operator,
        )

    def test_chatbot_enabled_condition(self):
        cases = [
            # condition - operator_available - expected_result
            ("only_if_no_operator", False, True),
            ("only_if_no_operator", True, False),
            ("only_if_operator", True, True),
            ("only_if_operator", False, False),
            ("always", False, True),
            ("always", True, True),
        ]
        for condition, operator_available, expected_result in cases:
            self.livechat_channel.user_ids.unlink()
            if operator_available:
                operator_user = new_test_user(
                    self.env,
                    login=f"operator_user_{condition}_{operator_available}_{expected_result}",
                    groups="im_livechat.im_livechat_group_user,base.group_user",
                )
                self.env["mail.presence"]._update_presence(operator_user)
                self.livechat_channel.user_ids = operator_user
            self.livechat_channel.rule_ids = self.env["im_livechat.channel.rule"].create(
                {
                    "channel_id": self.livechat_channel.id,
                    "chatbot_script_id": self.chatbot_script.id,
                    "chatbot_enabled_condition": condition,
                    "regex_url": "/",
                    "sequence": 1,
                }
            )
            matching_rule = (
                self.env["im_livechat.channel.rule"].match_rule(self.livechat_channel.id, "/")
                or self.env["im_livechat.channel.rule"]
            )
            self.assertEqual(
                matching_rule.chatbot_script_id,
                self.chatbot_script if expected_result else self.env["chatbot.script"],
                f"Condition: {condition}, Operator available: {operator_available}, Expected result: {expected_result}",
            )

    def test_chatbot_member_type(self):
        """Ensure livechat_member_type are correctly set when using chatbot with a logged in user."""
        self.authenticate(self.user_employee.login, self.user_employee.login)
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "chatbot_script_id": self.chatbot_script.id,
                "channel_id": self.livechat_channel.id,
            },
        )
        discuss_channel = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertEqual(
            discuss_channel.channel_member_ids.mapped("livechat_member_type"),
            ["bot", "visitor"],
        )

    def test_chatbot_clear_answers_on_step_type_change(self):
        chatbot = self.env['chatbot.script'].create({
            'title': 'Clear Answer Test Bot',
            'script_step_ids': [Command.create({
                'step_type': 'question_selection',
                'message': 'What do you want to do?',
                'answer_ids': [
                    Command.create({'name': 'Buy'}),
                    Command.create({'name': 'Support'}),
                ]
            })]
        })
        step = chatbot.script_step_ids[0]
        answers = {a.name: a for a in step.answer_ids}
        [step_2, step_3] = self.env['chatbot.script.step'].create([
            {
                'chatbot_script_id': chatbot.id,
                'step_type': 'text',
                'message': 'Great! Let me help you with buying.',
                'sequence': 2,
                'triggering_answer_ids': [Command.set(answers['Buy'].ids)],
            },
            {
                'chatbot_script_id': chatbot.id,
                'step_type': 'text',
                'message': 'Sure! I can assist you with support.',
                'sequence': 3,
                'triggering_answer_ids': [Command.set(answers['Support'].ids)],
            },
        ])
        action = self.env.ref('im_livechat.chatbot_script_action')
        self.start_tour(f"/odoo/action-{action.id}", 'change_chatbot_step_type', login='admin')
        self.assertFalse(step.answer_ids, "Answers were not cleared after step_type was changed.")
        self.assertFalse(step_2.triggering_answer_ids, "Step 2 still has stale triggering answers.")
        self.assertFalse(step_3.triggering_answer_ids, "Step 3 still has stale triggering answers.")
