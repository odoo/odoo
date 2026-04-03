# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import HttpCase, new_test_user, tagged, users
from odoo.tools.misc import mute_logger

from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store


@tagged("RTC")
class TestChannelRTC(MailCommon, HttpCase):
    @classmethod
    @freeze_time("2023-03-15 12:34:56")
    def setUpClass(cls):
        super().setUpClass()
        # clean up before test to avoid unexpected side effects
        cls.env["discuss.channel.rtc.session"].sudo().search([]).unlink()
        cls.env["mail.presence"]._update_presence(cls.guest)
        # ensure the pre-created records have the right env because all tests
        # are executed as employee and setUpClass as admin
        cls.test_user = new_test_user(
            cls.env,
            "test_user",
            groups="base.group_user",
            email="test_user@example.com",
        )
        cls.test_partner = cls.test_user.partner_id
        cls.channel_internal = (
            cls.env["discuss.channel"]
            .with_user(cls.user_employee)
            ._create_channel(
                name="A channel restricted to internal users with only user_employee inside",
                group_id=cls.env.ref("base.group_user").id,
            )
        )
        cls.member_of_employee_in_channel_internal = cls.channel_internal.self_member_id
        cls.chat = (
            cls.env["discuss.channel"]
            .with_user(cls.user_employee)
            ._get_or_create_chat(
                partners_to=cls.test_user.partner_id.ids,
            )
        )
        cls.member_of_employee_in_chat = cls.chat.self_member_id
        cls.member_of_test_user_in_chat = cls.chat.with_user(cls.test_user).self_member_id
        cls.channel_group_a = (
            cls.env["discuss.channel"]
            .with_user(cls.user_employee)
            ._create_group(
                partners_to=(cls.user_employee.partner_id + cls.test_user.partner_id).ids,
                name="A group with user_employee, test_user and guest inside",
            )
        )
        cls.channel_group_a._add_members(guests=cls.guest)
        cls.member_of_employee_in_group_a = cls.channel_group_a.self_member_id
        cls.member_of_test_user_in_group_a = cls.channel_group_a.with_user(
            cls.test_user,
        ).self_member_id
        cls.member_of_guest_in_group_a = cls.channel_group_a.channel_member_ids.filtered(
            lambda m: m.guest_id == cls.guest,
        )
        cls.channel_group_b = (
            cls.env["discuss.channel"]
            .with_user(cls.user_employee)
            ._create_group(
                partners_to=cls.user_employee.partner_id.ids,
                name="A group with only user_employee inside",
            )
        )
        cls.member_of_employee_in_group_b = cls.channel_group_b.self_member_id

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_01_join_call(self):
        """Join call should remove existing sessions, remove invitation, create a new session, and return data."""
        self.member_of_employee_in_channel_internal.sudo()._rtc_join_call()
        initial_rtc_session = self.member_of_employee_in_channel_internal.sudo().rtc_session_ids

        def notifications():
            message = self.env["mail.message"].search(
                [
                    ("model", "=", "discuss.channel"),
                    ("res_id", "=", self.channel_internal.id),
                    ("message_type", "=", "notification"),
                ],
                order="id desc",
                limit=1,
            )
            rtc_session = self.member_of_employee_in_channel_internal.sudo().rtc_session_ids
            call_history = self.channel_internal.call_history_ids.filtered("end_dt")
            return [
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": initial_rtc_session.id},
                ),
                BusResult(
                    self.channel_internal,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 0.0,
                                "end_dt": "2023-03-15 12:34:56",
                                "id": call_history.id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": self.channel_internal.id,
                                "rtc_session_ids": [("DELETE", initial_rtc_session.ids)],
                            },
                        ],
                    },
                ),
                BusResult(
                    self.user_employee,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_employee_in_channel_internal,
                                new_message_separator=message.id + 1,
                            ),
                        ],
                    },
                ),
                BusResult(self.channel_internal, "discuss.channel/new_message"),
                BusResult(
                    self.channel_internal,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_internal.id,
                                "rtc_session_ids": [("ADD", rtc_session.ids)],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_employee_in_channel_internal),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session),
                        ],
                        "mail.message": [
                            {
                                "call_history_ids": message.call_history_ids.ids,
                                "id": message.id,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.partner_employee, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.user_employee),
                        ),
                    },
                ),
            ]

        with self.assertBus(notifications):
            store = Store()
            self.member_of_employee_in_channel_internal.sudo()._rtc_join_call(store)
            res = store._build_result()
        rtc_session = self.member_of_employee_in_channel_internal.sudo().rtc_session_ids
        self.assertEqual(
            res,
            {
                "discuss.channel": [
                    {
                        "id": self.channel_internal.id,
                        "rtc_session_ids": [
                            ("ADD", rtc_session.ids),
                            ("DELETE", initial_rtc_session.ids),
                        ],
                    },
                ],
                "discuss.channel.member": [
                    self._res_for_member(self.member_of_employee_in_channel_internal),
                ],
                "discuss.channel.rtc.session": [
                    self._res_for_rtc_session(rtc_session),
                ],
                "res.partner": self._filter_partners_fields(
                    self._res_for_partner(self.partner_employee, internal=True),
                ),
                "res.users": self._filter_users_fields(
                    self._res_for_user(self.user_employee),
                ),
                "Rtc": {
                    "iceServers": False,
                    "localSession": rtc_session.id,
                    "serverInfo": None,
                },
            },
        )

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_10_start_call_in_chat_should_invite_all_members_to_call(self):
        self.member_of_employee_in_chat.sudo()._rtc_join_call()
        self.member_of_employee_in_chat.sudo()._rtc_leave_call()

        def notifications():
            message = self.env["mail.message"].search(
                [
                    ("model", "=", "discuss.channel"),
                    ("res_id", "=", self.chat.id),
                    ("message_type", "=", "notification"),
                ],
                order="id desc",
                limit=1,
            )
            rtc_session = self.member_of_employee_in_chat.sudo().rtc_session_ids
            return [
                BusResult(
                    # update new message separator (message_post)
                    self.user_employee,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_employee_in_chat,
                                new_message_separator=message.id + 1,
                            ),
                        ],
                    },
                ),
                BusResult(self.chat, "discuss.channel/new_message"),
                BusResult(
                    self.chat,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.chat.id,
                                "rtc_session_ids": [("ADD", rtc_session.ids)],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_employee_in_chat),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session),
                        ],
                        "mail.message": [
                            {
                                "call_history_ids": message.call_history_ids.ids,
                                "id": message.id,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.partner_employee),
                        ),
                    },
                ),
                BusResult(
                    (self.chat, "internal_users"),
                    "mail.record/insert",
                    {
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(
                                self.partner_employee,
                                common=False,
                                internal=True,
                            ),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.user_employee),
                        ),
                    },
                ),
                BusResult(
                    # incoming invitation
                    self.test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_test_user_in_chat,
                                rtc_inviting_session_id=rtc_session.id,
                            ),
                            self._res_for_member(self.member_of_employee_in_chat),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session, extra=True),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.partner_employee, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.user_employee),
                        ),
                    },
                ),
                BusResult(
                    self.chat,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.chat.id,
                                "invited_member_ids": [
                                    ("ADD", self.member_of_test_user_in_chat.ids),
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_test_user_in_chat),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner),
                        ),
                    },
                ),
                BusResult(
                    (self.chat, "internal_users"),
                    "mail.record/insert",
                    {
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner, common=False, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.test_user),
                        ),
                    },
                ),
            ]

        with self.assertBus(notifications):
            now = fields.Datetime.now()
            with patch.object(fields.Datetime, "now", lambda: now + relativedelta(seconds=5)):
                self.member_of_employee_in_chat.sudo()._rtc_join_call()

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_11_start_call_in_group_should_invite_all_members_to_call(self):
        self.member_of_employee_in_group_a.sudo()._rtc_join_call()
        self.member_of_employee_in_group_a.sudo()._rtc_leave_call()

        def notifications():
            message = self.env["mail.message"].search(
                [
                    ("model", "=", "discuss.channel"),
                    ("res_id", "=", self.channel_group_a.id),
                    ("message_type", "=", "notification"),
                ],
                order="id desc",
                limit=1,
            )
            rtc_session = self.member_of_employee_in_group_a.sudo().rtc_session_ids
            return [
                BusResult(
                    self.user_employee,
                    # Update of the author's member record after posting the call message.
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_employee_in_group_a,
                                new_message_separator=message.id + 1,
                            ),
                        ],
                    },
                ),
                BusResult(self.channel_group_a, "discuss.channel/new_message"),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "rtc_session_ids": [("ADD", rtc_session.ids)],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_employee_in_group_a),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session),
                        ],
                        "mail.message": [
                            {
                                "call_history_ids": message.call_history_ids.ids,
                                "id": message.id,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.partner_employee),
                        ),
                    },
                ),
                BusResult(
                    (self.channel_group_a, "internal_users"),
                    "mail.record/insert",
                    {
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(
                                self.partner_employee,
                                common=False,
                                internal=True,
                            ),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.user_employee),
                        ),
                    },
                ),
                BusResult(
                    # incoming invitation
                    self.test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_test_user_in_group_a,
                                rtc_inviting_session_id=rtc_session.id,
                            ),
                            self._res_for_member(self.member_of_employee_in_group_a),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session, extra=True),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.partner_employee, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.user_employee),
                        ),
                    },
                ),
                BusResult(
                    # incoming invitation
                    self.guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_guest_in_group_a,
                                rtc_inviting_session_id=rtc_session.id,
                            ),
                            self._res_for_member(self.member_of_employee_in_group_a),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session, extra=True),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.partner_employee),
                        ),
                    },
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "invited_member_ids": [
                                    (
                                        "ADD",
                                        (
                                            self.member_of_test_user_in_group_a
                                            + self.member_of_guest_in_group_a
                                        ).ids,
                                    ),
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_test_user_in_group_a),
                            self._res_for_member(self.member_of_guest_in_group_a),
                        ],
                        "mail.guest": [
                            self._res_for_guest(self.guest),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner),
                        ),
                    },
                ),
                BusResult(
                    (self.channel_group_a, "internal_users"),
                    "mail.record/insert",
                    {
                        "mail.guest": [
                            self._res_for_guest(self.guest, common=False, internal=True),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner, common=False, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.test_user),
                        ),
                    },
                ),
            ]

        with self.assertBus(notifications):
            now = fields.Datetime.now()
            with patch.object(fields.Datetime, "now", lambda: now + relativedelta(seconds=5)):
                self.member_of_employee_in_group_a.sudo()._rtc_join_call()

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_20_join_call_should_cancel_pending_invitations(self):
        self.member_of_employee_in_group_a.sudo()._rtc_join_call()

        def notifications():
            rtc_session = self.member_of_test_user_in_group_a.sudo().rtc_session_ids
            return [
                BusResult(
                    self.test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_test_user_in_group_a,
                                rtc_inviting_session_id=False,
                            ),
                        ],
                    },
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "invited_member_ids": [
                                    ("DELETE", self.member_of_test_user_in_group_a.ids),
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_test_user_in_group_a),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner),
                        ),
                    },
                ),
                BusResult(
                    (self.channel_group_a, "internal_users"),
                    "mail.record/insert",
                    {
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner, common=False, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.test_user),
                        ),
                    },
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "rtc_session_ids": [("ADD", rtc_session.ids)],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_test_user_in_group_a),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner),
                        ),
                    },
                ),
                BusResult(
                    (self.channel_group_a, "internal_users"),
                    "mail.record/insert",
                    {
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner, common=False, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.test_user),
                        ),
                    },
                ),
            ]

        with self.assertBus(notifications):
            self.member_of_test_user_in_group_a.sudo()._rtc_join_call()

        def notifications_2():
            rtc_session = self.member_of_guest_in_group_a.sudo().rtc_session_ids
            return [
                BusResult(
                    self.guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_guest_in_group_a,
                                rtc_inviting_session_id=False,
                            ),
                        ],
                    },
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "invited_member_ids": [
                                    ("DELETE", self.member_of_guest_in_group_a.ids),
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_guest_in_group_a),
                        ],
                        "mail.guest": [
                            self._res_for_guest(self.guest),
                        ],
                    },
                ),
                BusResult(
                    (self.channel_group_a, "internal_users"),
                    "mail.record/insert",
                    {
                        "mail.guest": [
                            self._res_for_guest(self.guest, common=False, internal=True),
                        ],
                    },
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "rtc_session_ids": [("ADD", rtc_session.ids)],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_guest_in_group_a),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session),
                        ],
                        "mail.guest": [
                            self._res_for_guest(self.guest),
                        ],
                    },
                ),
                BusResult(
                    (self.channel_group_a, "internal_users"),
                    "mail.record/insert",
                    {
                        "mail.guest": [
                            self._res_for_guest(self.guest, common=False, internal=True),
                        ],
                    },
                ),
            ]

        with self.assertBus(notifications_2):
            self.member_of_guest_in_group_a.sudo()._rtc_join_call()

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_21_leave_call_should_cancel_pending_invitations(self):
        self.channel_group_a._add_members(guests=self.guest)
        self.member_of_employee_in_group_a.sudo()._rtc_join_call()
        with self.assertBus(
            [
                BusResult(
                    self.test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_test_user_in_group_a,
                                rtc_inviting_session_id=False,
                            ),
                        ],
                    },
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "invited_member_ids": [
                                    ("DELETE", self.member_of_test_user_in_group_a.ids),
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_test_user_in_group_a),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner),
                        ),
                    },
                ),
                BusResult(
                    (self.channel_group_a, "internal_users"),
                    "mail.record/insert",
                    {
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner, common=False, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.test_user),
                        ),
                    },
                ),
            ],
        ):
            self.member_of_test_user_in_group_a.sudo()._rtc_leave_call()

        with self.assertBus(
            [
                BusResult(
                    self.guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_guest_in_group_a,
                                rtc_inviting_session_id=False,
                            ),
                        ],
                    },
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "invited_member_ids": [
                                    ("DELETE", self.member_of_guest_in_group_a.ids),
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_guest_in_group_a),
                        ],
                        "mail.guest": [
                            self._res_for_guest(self.guest),
                        ],
                    },
                ),
                BusResult(
                    (self.channel_group_a, "internal_users"),
                    "mail.record/insert",
                    {
                        "mail.guest": [
                            self._res_for_guest(self.guest, common=False, internal=True),
                        ],
                    },
                ),
            ],
        ):
            self.member_of_guest_in_group_a.sudo()._rtc_leave_call()

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_25_lone_call_participant_leaving_call_should_cancel_pending_invitations(self):
        self.channel_group_a._add_members(guests=self.guest)
        self.member_of_employee_in_group_a.sudo()._rtc_join_call()
        last_rtc_session = self.member_of_employee_in_group_a.sudo().rtc_session_ids
        with self.assertBus(
            [
                BusResult(
                    self.test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_test_user_in_group_a,
                                rtc_inviting_session_id=False,
                            ),
                        ],
                    },
                ),
                BusResult(
                    self.guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_guest_in_group_a,
                                rtc_inviting_session_id=False,
                            ),
                        ],
                    },
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "invited_member_ids": [
                                    (
                                        "DELETE",
                                        (
                                            self.member_of_test_user_in_group_a
                                            + self.member_of_guest_in_group_a
                                        ).ids,
                                    ),
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(self.member_of_test_user_in_group_a),
                            self._res_for_member(self.member_of_guest_in_group_a),
                        ],
                        "mail.guest": [
                            self._res_for_guest(self.guest),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner),
                        ),
                    },
                ),
                BusResult(
                    (self.channel_group_a, "internal_users"),
                    "mail.record/insert",
                    {
                        "mail.guest": [
                            self._res_for_guest(self.guest, common=False, internal=True),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner, common=False, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.test_user),
                        ),
                    },
                ),
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": last_rtc_session.id},
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 0.0,
                                "end_dt": "2023-03-15 12:34:56",
                                "id": self.channel_group_a.call_history_ids.id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "rtc_session_ids": [("DELETE", last_rtc_session.ids)],
                            },
                        ],
                    },
                ),
            ],
        ):
            self.member_of_employee_in_group_a.sudo()._rtc_leave_call()

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_30_add_members_while_in_call_should_invite_new_members_to_call(self):
        now = fields.Datetime.now()
        with patch.object(fields.Datetime, "now", lambda: now + relativedelta(seconds=5)):
            self.member_of_employee_in_group_b.sudo()._rtc_join_call()

        def notifications():
            member_of_test_user = self.channel_group_b.channel_member_ids.filtered(
                lambda member: member.partner_id == self.test_partner,
            )
            member_of_guest = self.channel_group_b.channel_member_ids.filtered(
                lambda member: member.guest_id == self.guest,
            )
            rtc_session_of_employee = self.member_of_employee_in_group_b.sudo().rtc_session_ids
            return [
                # discuss.channel (channel_name_member_ids)
                BusResult(self.channel_group_b, "mail.record/insert"),
                BusResult((self.channel_group_b, "internal_users"), "mail.record/insert"),
                BusResult(self.test_user, "discuss.channel/joined"),
                # discuss.channel.member (message_unread_counter, new_message_separator, …)
                BusResult(self.user_employee, "mail.record/insert"),
                BusResult(self.channel_group_b, "discuss.channel/new_message"),
                BusResult(self.guest, "discuss.channel/joined"),
                # discuss.channel.member (message_unread_counter, new_message_separator, …)
                BusResult(self.user_employee, "mail.record/insert"),
                BusResult(self.channel_group_b, "discuss.channel/new_message"),
                # discuss.channel (member_count), discuss.channel.member
                BusResult(self.channel_group_b, "mail.record/insert"),
                BusResult((self.channel_group_b, "internal_users"), "mail.record/insert"),
                BusResult(
                    self.test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                member_of_test_user,
                                rtc_inviting_session_id=member_of_test_user.rtc_inviting_session_id.id,
                            ),
                            self._res_for_member(self.member_of_employee_in_group_b),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session_of_employee, extra=True),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.partner_employee, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.user_employee),
                        ),
                    },
                ),
                BusResult(
                    self.guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                member_of_guest,
                                rtc_inviting_session_id=member_of_guest.rtc_inviting_session_id.id,
                            ),
                            self._res_for_member(self.member_of_employee_in_group_b),
                        ],
                        "discuss.channel.rtc.session": [
                            self._res_for_rtc_session(rtc_session_of_employee, extra=True),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.partner_employee),
                        ),
                    },
                ),
                BusResult(
                    self.channel_group_b,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_b.id,
                                "invited_member_ids": [
                                    (
                                        "ADD",
                                        [member_of_test_user.id, member_of_guest.id],
                                    ),
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            self._res_for_member(member_of_test_user),
                            self._res_for_member(member_of_guest),
                        ],
                        "mail.guest": [
                            self._res_for_guest(self.guest),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner),
                        ),
                    },
                ),
                BusResult(
                    (self.channel_group_b, "internal_users"),
                    "mail.record/insert",
                    {
                        "mail.guest": [
                            self._res_for_guest(self.guest, common=False, internal=True),
                        ],
                        "res.partner": self._filter_partners_fields(
                            self._res_for_partner(self.test_partner, common=False, internal=True),
                        ),
                        "res.users": self._filter_users_fields(
                            self._res_for_user(self.test_user),
                        ),
                    },
                ),
            ]

        with self.assertBus(notifications):
            with patch.object(fields.Datetime, "now", lambda: now + relativedelta(seconds=10)):
                self.channel_group_b._add_members(
                    users=self.test_user,
                    guests=self.guest,
                    invite_to_rtc_call=True,
                )

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_40_leave_call_should_remove_existing_sessions_of_user_in_channel_and_return_data(self):
        self.member_of_employee_in_group_b.sudo()._rtc_join_call()
        last_rtc_session = self.member_of_employee_in_group_b.sudo().rtc_session_ids
        with self.assertBus(
            [
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": last_rtc_session.id},
                ),
                BusResult(
                    self.channel_group_b,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 1.0,
                                "end_dt": "2023-03-15 13:34:56",
                                "id": self.channel_group_b.call_history_ids.id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": self.channel_group_b.id,
                                "rtc_session_ids": [["DELETE", last_rtc_session.ids]],
                            },
                        ],
                    },
                ),
            ],
        ):
            now = fields.Datetime.now()
            with patch.object(fields.Datetime, "now", lambda: now + relativedelta(hours=1)):
                self.member_of_employee_in_group_b.sudo()._rtc_leave_call()

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_50_garbage_collect_should_remove_old_sessions_and_notify_data(self):
        self.member_of_employee_in_group_b.sudo()._rtc_join_call()
        self.env["discuss.channel.rtc.session"].flush_model()
        self.member_of_employee_in_group_b.sudo().rtc_session_ids._write(
            {"write_date": fields.Datetime.now() - relativedelta(days=2)},
        )
        last_rtc_session = self.member_of_employee_in_group_b.sudo().rtc_session_ids
        with self.assertBus(
            [
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": last_rtc_session.id},
                ),
                BusResult(
                    self.channel_group_b,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 0.0,
                                "end_dt": "2023-03-15 12:34:56",
                                "id": self.channel_group_b.call_history_ids.id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": self.channel_group_b.id,
                                "rtc_session_ids": [("DELETE", last_rtc_session.ids)],
                            },
                        ],
                    },
                ),
            ],
        ):
            self.env["discuss.channel.rtc.session"].sudo()._gc_inactive_sessions()
        self.assertFalse(self.member_of_employee_in_group_b.sudo().rtc_session_ids)

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_51_action_disconnect_should_remove_selected_session_and_notify_data(self):
        self.member_of_employee_in_group_b.sudo()._rtc_join_call()
        last_rtc_session = self.member_of_employee_in_group_b.sudo().rtc_session_ids
        with self.assertBus(
            [
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": last_rtc_session.id},
                ),
                BusResult(
                    self.channel_group_b,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 0.0,
                                "end_dt": "2023-03-15 12:34:56",
                                "id": self.channel_group_b.call_history_ids.id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": self.channel_group_b.id,
                                "rtc_session_ids": [("DELETE", last_rtc_session.ids)],
                            },
                        ],
                    },
                ),
            ],
        ):
            self.member_of_employee_in_group_b.sudo().rtc_session_ids.action_disconnect()
        self.assertFalse(self.member_of_employee_in_group_b.sudo().rtc_session_ids)

    @users("employee")
    @mute_logger("odoo.models.unlink")
    @freeze_time("2023-03-15 12:34:56")
    def test_60_rtc_sync_sessions_should_gc_and_return_outdated_and_active_sessions(self):
        store = Store()
        self.member_of_employee_in_group_a.sudo()._rtc_join_call(store)
        join_call_values = store._build_result()
        test_session = (
            self.env["discuss.channel.rtc.session"]
            .sudo()
            .create({"channel_member_id": self.member_of_guest_in_group_a.id})
        )
        test_session.flush_model()
        test_session._write({"write_date": fields.Datetime.now() - relativedelta(days=2)})
        unused_ids = [9998, 9999]
        with self.assertBus(
            [
                BusResult(
                    self.guest,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": test_session.id},
                ),
                BusResult(
                    self.channel_group_a,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": self.channel_group_a.id,
                                "rtc_session_ids": [("DELETE", test_session.ids)],
                            },
                        ],
                    },
                ),
            ],
        ):
            current_rtc_sessions, outdated_rtc_sessions = (
                self.member_of_employee_in_group_a.sudo()._rtc_sync_sessions(
                    check_rtc_session_ids=[join_call_values["Rtc"]["localSession"]] + unused_ids,
                )
            )
        self.assertEqual(
            self.member_of_employee_in_group_a.sudo().rtc_session_ids,
            current_rtc_sessions,
        )
        self.assertEqual(unused_ids, outdated_rtc_sessions.ids)
        self.assertFalse(outdated_rtc_sessions.exists())

    @freeze_time("2023-03-15 12:34:56")
    def test_70_call_invitation_ui(self):
        self.member_of_employee_in_group_a.sudo()._rtc_join_call()
        self._reset_bus()
        self.start_tour("/odoo", "discuss_call_invitation.js", login="test_user")

    def _res_for_guest(self, guest, common=True, internal=False):
        res = {"id": guest.id}
        if common:
            res["avatar_128_access_token"] = guest._get_avatar_128_access_token()
            res["id"] = guest.id
            res["name"] = guest.name
            res["write_date"] = fields.Datetime.to_string(guest.write_date)
        if internal:
            res["im_status"] = guest.im_status
            res["im_status_access_token"] = guest._get_im_status_access_token()
        return res

    def _res_for_member(self, member, **kwargs):
        res = {
            "channel_id": member.channel_id.id,
            "id": member.id,
            **kwargs,
        }
        if member.partner_id:
            res["partner_id"] = member.partner_id.id
        if member.guest_id:
            res["guest_id"] = member.guest_id.id
        return res

    def _res_for_partner(self, partner, common=True, internal=False):
        res = {"id": partner.id}
        if common:
            res["avatar_128_access_token"] = partner._get_avatar_128_access_token()
            res["mention_token"] = partner._get_mention_token()
            res["name"] = partner.name
            res["write_date"] = fields.Datetime.to_string(partner.write_date)
        if internal:
            res["im_status"] = partner.im_status
            res["im_status_access_token"] = partner._get_im_status_access_token()
            res["main_user_id"] = partner.main_user_id.id
        return res

    def _res_for_rtc_session(self, rtc_session, extra=False):
        res = {
            "id": rtc_session.id,
            "channel_member_id": rtc_session.channel_member_id.id,
        }
        if extra:
            res["is_camera_on"] = rtc_session.is_camera_on
            res["is_deaf"] = rtc_session.is_deaf
            res["is_muted"] = rtc_session.is_muted
            res["is_screen_sharing_on"] = rtc_session.is_screen_sharing_on
        return res

    def _res_for_user(self, user):
        return {
            "employee_ids": [],
            "id": user.id,
            "partner_id": user.partner_id.id,
        }
