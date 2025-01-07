# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
import json

from odoo import Command, fields
from odoo.addons.im_livechat.tests import chatbot_common
from odoo.tests.common import JsonRpcException, new_test_user, tagged
from odoo.tools.misc import mute_logger
from odoo.addons.bus.models.bus import json_dump
from odoo.addons.mail.tools.discuss import Store


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

    @freeze_time("2020-03-22 10:42:06")
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
        self.assertEqual(discuss_channel.name, "Testing Bot")

        member_bot = discuss_channel.channel_member_ids.filtered(
            lambda m: m.partner_id == self.chatbot_script.operator_partner_id
        )
        member_bot_data = {
            "create_date": fields.Datetime.to_string(member_bot.create_date),
            "fetched_message_id": False,
            "id": member_bot.id,
            "is_bot": True,
            "last_seen_dt": False,
            "persona": {"id": member_bot.partner_id.id, "type": "partner"},
            "seen_message_id": False,
            "thread": {"id": discuss_channel.id, "model": "discuss.channel"},
        }

        def get_forward_op_bus_params():
            messages = self.env["mail.message"].search([], order="id desc", limit=3)
            # only data relevant to the test are asserted for simplicity
            transfer_message_data = Store(messages[2]).get_result()
            transfer_message_data["mail.message"][0].update(
                {
                    "author": {"id": self.chatbot_script.operator_partner_id.id, "type": "partner"},
                    "body": "<p>I will transfer you to a human.</p>",
                    # thread not renamed yet at this step
                    "default_subject": "Testing Bot",
                    "record_name": "Testing Bot",
                }
            )
            transfer_message_data["mail.thread"][0]["display_name"] = "Testing Bot"
            joined_message_data = Store(messages[1]).get_result()
            joined_message_data["mail.message"][0].update(
                {
                    "author": {"id": self.partner_employee.id, "type": "partner"},
                    "body": "<div class=\"o_mail_notification\">joined the channel</div>",
                    # thread not renamed yet at this step
                    "default_subject": "Testing Bot",
                    "record_name": "Testing Bot",
                }
            )
            joined_message_data["mail.thread"][0]["display_name"] = "Testing Bot"
            left_message_data = Store(messages[0]).get_result()
            left_message_data["mail.message"][0].update(
                {
                    "author": {"id": self.chatbot_script.operator_partner_id.id, "type": "partner"},
                    "body": '<div class="o_mail_notification">left the channel</div>',
                    # thread not renamed yet at this step
                    "default_subject": "Testing Bot",
                    "record_name": "Testing Bot",
                }
            )
            left_message_data["mail.thread"][0]["display_name"] = "Testing Bot"
            member_emp = discuss_channel.channel_member_ids.filtered(
                lambda m: m.partner_id == self.partner_employee
            )
            # data in-between join and leave
            channel_data_join = json.loads(
                json_dump(
                    Store(
                        discuss_channel, discuss_channel._to_store_defaults(for_current_user=False)
                    ).get_result()
                )
            )
            channel_data_join["discuss.channel"][0]["chatbot"]["currentStep"]["message"] = messages[2].id
            channel_data_join["discuss.channel"][0]["chatbot"]["steps"][0]["message"] = messages[2].id
            channel_data_join["discuss.channel"][0]["is_pinned"] = True
            channel_data_join["discuss.channel"][0]["livechat_operator_id"] = {
                "id": self.chatbot_script.operator_partner_id.id,
                "type": "partner",
            }
            channel_data_join["discuss.channel"][0]["member_count"] = 3
            channel_data_join["discuss.channel"][0]["name"] = "Testing Bot"
            channel_data_join["discuss.channel.member"].insert(0, member_bot_data)
            channel_data_join["discuss.channel.member"][2]["fetched_message_id"] = False
            channel_data_join["discuss.channel.member"][2]["last_seen_dt"] = False
            channel_data_join["discuss.channel.member"][2]["seen_message_id"] = False
            del channel_data_join["res.partner"][1]
            channel_data_join["res.partner"].insert(
                0,
                {
                    "active": False,
                    "country": False,
                    "id": self.chatbot_script.operator_partner_id.id,
                    "is_public": False,
                    "name": "Testing Bot",
                    "user_livechat_username": False,
                    "write_date": fields.Datetime.to_string(self.chatbot_script.operator_partner_id.write_date),
                },
            )
            channel_data = Store(discuss_channel).get_result()
            channel_data["discuss.channel"][0]["message_needaction_counter_bus_id"] = 0
            channel_data_emp = Store(discuss_channel.with_user(self.user_employee)).get_result()
            channel_data_emp["discuss.channel"][0]["message_needaction_counter_bus_id"] = 0
            channel_data_emp["discuss.channel.member"][1]["message_unread_counter_bus_id"] = 0
            channel_data = Store(discuss_channel).get_result()
            channel_data["discuss.channel"][0]["message_needaction_counter_bus_id"] = 0
            return (
                [
                    (self.cr.dbname, "discuss.channel", discuss_channel.id, "members"),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "res.partner", self.partner_employee.id),
                    (self.cr.dbname, "res.partner", self.partner_employee.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id, "members"),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id, "members"),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "res.partner", self.chatbot_script.operator_partner_id.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "discuss.channel", discuss_channel.id),
                    (self.cr.dbname, "res.partner", self.partner_employee.id),
                    (self.cr.dbname, "res.partner", self.env.user.partner_id.id),
                ],
                [
                    {
                        "type": "mail.record/insert",
                        "payload": {
                            "discuss.channel": [{"id": discuss_channel.id, "is_pinned": True}]
                        },
                    },
                    {
                        "type": "discuss.channel/new_message",
                        "payload": {
                            "data": transfer_message_data,
                            "id": discuss_channel.id,
                        },
                    },
                    {
                        "type": "discuss.channel/joined",
                        "payload": {"channel_id": discuss_channel.id, "data": channel_data_join},
                    },
                    {
                        "type": "mail.record/insert",
                        "payload": {
                            "discuss.channel.member": [
                                {
                                    "id": member_emp.id,
                                    "message_unread_counter": 0,
                                    "message_unread_counter_bus_id": 0,
                                    "new_message_separator": messages[0].id,
                                    "persona": {"id": self.partner_employee.id, "type": "partner"},
                                    "syncUnread": True,
                                    "thread": {
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
                                    "country": self.env.ref("base.be").id,
                                    "id": self.partner_employee.id,
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
                            "discuss.channel": [{"id": discuss_channel.id, "is_pinned": True}]
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
                                    "fetched_message_id": messages[1].id,
                                    "id": member_emp.id,
                                    "is_bot": False,
                                    "last_seen_dt": fields.Datetime.to_string(
                                        member_emp.last_seen_dt
                                    ),
                                    "persona": {"id": self.partner_employee.id, "type": "partner"},
                                    "seen_message_id": messages[1].id,
                                    "thread": {
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
                                    "country": self.env.ref("base.be").id,
                                    "id": self.partner_employee.id,
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
                            "discuss.channel": [{"id": discuss_channel.id, "is_pinned": True}]
                        },
                    },
                    {
                        "type": "discuss.channel/new_message",
                        "payload": {"data": left_message_data, "id": discuss_channel.id},
                    },
                    {
                        "type": "discuss.channel/leave",
                        "payload": {
                            "discuss.channel": [
                                {
                                    "id": discuss_channel.id,
                                    "isLocallyPinned": False,
                                    "is_pinned": False,
                                }
                            ]
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
                                    "livechat_operator_id": {"id": self.partner_employee.id, "type": "partner"},
                                    "name": "OdooBot Ernest Employee",
                                },
                            ],
                            "res.partner": self._filter_partners_fields(
                                {
                                    "id": self.partner_employee.id,
                                    "name": "Ernest Employee",
                                    "user_livechat_username": False,
                                    "write_date": fields.Datetime.to_string(
                                        self.partner_employee.write_date
                                    ),
                                }
                            ),
                        },
                    },
                    {"type": "mail.record/insert", "payload": channel_data_emp},
                    {"type": "mail.record/insert", "payload": channel_data},
                ],
            )

        self._reset_bus()
        with self.assertBus(get_params=get_forward_op_bus_params):
            self.step_forward_operator._process_step_forward_operator(
                discuss_channel, users=self.user_employee
            )
        self.assertEqual(discuss_channel.name, "OdooBot Ernest Employee")
        self.assertEqual(discuss_channel.livechat_operator_id, self.partner_employee)

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
                    "chatbot_only_if_no_operator": True,
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
        self.env["bus.presence"]._update_presence(
            inactivity_period=0, identity_field="user_id", identity_value=bob_user.id
        )
        # Force the recomputation of `available_operator_ids` after bob becomes online
        self.livechat_channel.invalidate_recordset(["available_operator_ids"])
        self.assertTrue(self.livechat_channel.available_operator_ids)
        self.assertEqual(
            self.env["im_livechat.channel.rule"]
            .match_rule(self.livechat_channel.id, "/")
            .chatbot_script_id,
            chatbot_operator,
        )
