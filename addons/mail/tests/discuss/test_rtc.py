# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC
from types import SimpleNamespace
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from werkzeug.exceptions import NotFound

from odoo import fields
from odoo.tests.common import HttpCase, new_test_user, tagged, users
from odoo.tools.misc import mute_logger

from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.controllers.discuss.rtc import _check_jwt
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools import jwt
from odoo.addons.mail.tools.discuss import Store, get_sfu_channel_key, get_sfu_channel_seed


SFU_KEY = "u6bsUQEWrHdKIuYplirRnbBmLbrKV5PxKG7DtA71mng="


@tagged("RTC")
class TestChannelRTC(MailCommon, HttpCase):
    @classmethod
    @freeze_time("2023-03-15 12:34:56")
    def setUpClass(cls):
        super().setUpClass()
        # clean up before test to avoid unexpected side effects
        cls.env["discuss.channel.rtc.session"].sudo().search([]).unlink()
        cls.env["ir.config_parameter"].set_str("mail.sfu_server_key", SFU_KEY)
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
                users_to=cls.user_employee + cls.test_user,
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
                users_to=cls.user_employee,
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
                                message_unread_counter=0,
                                message_unread_counter_bus_id=0,
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
                            self._res_for_user(self.user_employee, internal=True),
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
                    self._res_for_user(self.user_employee, internal=True),
                ),
                "Rtc": {
                    "iceServers": False,
                    "canRecordTranscription": False,
                    "canRecordVideo": False,
                    "canRecordAudio": False,
                    "localSession": rtc_session.id,
                    "serverInfo": None,
                },
            },
        )

    def test_02_recording_permissions_internal_only(self):
        portal_user = new_test_user(
            self.env,
            "recording_portal_user",
            groups="base.group_portal",
            email="recording_portal_user@example.com",
        )
        expected_permissions = {
            "transcription": False,
            "audioRecording": True,
            "videoRecording": True,
        }
        self.assertEqual(
            self.member_of_employee_in_group_a._get_recording_permissions(self.partner_employee),
            expected_permissions,
        )
        expected_permissions = dict.fromkeys(expected_permissions, False)
        self.assertEqual(
            self.member_of_employee_in_group_a._get_recording_permissions(portal_user.partner_id),
            expected_permissions,
        )
        self.assertEqual(
            self.member_of_employee_in_group_a._get_recording_permissions(self.env["res.partner"]),
            expected_permissions,
        )

    def test_03_transcription_route_is_unavailable_without_ai(self):
        call_start = fields.Datetime.now()
        call = self.env["discuss.call.history"].create({
            "channel_id": self.channel_group_a.id,
            "start_dt": call_start,
        })
        call_start_ms = int(call_start.replace(tzinfo=UTC).timestamp() * 1000)
        token = jwt.sign(
            {"iat": int(call_start.replace(tzinfo=UTC).timestamp())},
            get_sfu_channel_key(self.env, self.channel_group_a.id),
            ttl=60,
            algorithm=jwt.Algorithm.HS256,
        )
        response = self.url_open(
            f"/mail/rtc/recording/{call.id}/transcribe",
            data=b"audio",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "audio/ogg",
            },
            params={
                "start_ms": call_start_ms + 1_000,
                "end_ms": call_start_ms + 3_000,
            },
        )

        self.assertEqual(response.status_code, 404)
        call.invalidate_recordset(["artifact_ids"])
        self.assertFalse(call.artifact_ids)

    def test_04_recording_routing_rejects_session_token(self):
        call_start = fields.Datetime.now()
        call = self.env["discuss.call.history"].create({
            "channel_id": self.channel_group_a.id,
            "start_dt": call_start,
        })
        token = jwt.sign(
            {"session_id": 1},
            get_sfu_channel_key(self.env, self.channel_group_a.id),
            ttl=60,
            algorithm=jwt.Algorithm.HS256,
        )
        routing_response = self.url_open(
            f"/mail/rtc/recording/{call.id}/routing",
            headers={"Authorization": f"Bearer {token}"},
            params={"start_ms": 1_000, "end_ms": 3_000},
        )

        self.assertEqual(routing_response.status_code, 404)

    def test_05_recording_jwt_returns_partner(self):
        now = fields.Datetime.now()
        channel_key = get_sfu_channel_key(self.env, self.channel_group_a.id)
        request = SimpleNamespace(
            env=self.env,
            httprequest=SimpleNamespace(headers={}),
        )

        def check_claims(**claims):
            token = jwt.sign(
                {"iat": int(now.replace(tzinfo=UTC).timestamp()), **claims},
                channel_key,
                ttl=60,
                algorithm=jwt.Algorithm.HS256,
            )
            request.httprequest.headers["Authorization"] = f"Bearer {token}"
            return _check_jwt(request, self.channel_group_a)

        claims = check_claims(partner_id=self.partner_employee.id)
        self.assertEqual(claims["partner_id"], self.partner_employee.id)
        self.assertNotIn("partner_id", check_claims())
        for malformed_partner_id in (True, "1", None, 0, -1):
            with self.assertRaises(NotFound):
                check_claims(partner_id=malformed_partner_id)

    @users("employee")
    def test_06_sfu_provisioning_sends_channel_seed(self):
        rtc_sessions = self.env["discuss.channel.rtc.session"].sudo().create([
            {"channel_member_id": member.id}
            for member in (
                self.member_of_employee_in_group_a,
                self.member_of_test_user_in_group_a,
                self.member_of_guest_in_group_a,
            )
        ])
        params = self.env["ir.config_parameter"].sudo()
        params.set_bool("mail.use_call_server", True)
        params.set_bool("mail.use_sfu_server", True)
        params.set_str("mail.sfu_server_url", "https://sfu.example.com")

        with patch(
            "odoo.addons.mail.models.discuss.discuss_channel_member.requests.get",
        ) as get_channel:
            get_channel.return_value.json.return_value = {
                "uuid": "sfu-channel-uuid",
                "url": "https://sfu.example.com",
            }
            self.member_of_employee_in_group_a.sudo()._join_sfu()

        authorization = get_channel.call_args.kwargs["headers"]["Authorization"]
        claims = jwt.verify(
            authorization.removeprefix("Bearer "),
            SFU_KEY,
            algorithm=jwt.Algorithm.HS256,
        )
        self.assertEqual(
            claims["keySeed"],
            get_sfu_channel_seed(self.env, self.channel_group_a.id),
        )
        self.assertNotIn("key", claims)

        server_info = self.member_of_employee_in_group_a.sudo()._get_rtc_server_info(rtc_sessions[0])
        client_claims = jwt.verify(
            server_info["jsonWebToken"],
            get_sfu_channel_key(self.env, self.channel_group_a.id),
            algorithm=jwt.Algorithm.HS256,
        )
        self.assertEqual(client_claims["session_id"], rtc_sessions[0].id)
        self.assertEqual(client_claims["partner_id"], self.partner_employee.id)

        guest_server_info = self.member_of_guest_in_group_a.sudo()._get_rtc_server_info(
            rtc_sessions[2],
        )
        guest_claims = jwt.verify(
            guest_server_info["jsonWebToken"],
            get_sfu_channel_key(self.env, self.channel_group_a.id),
            algorithm=jwt.Algorithm.HS256,
        )
        self.assertNotIn("partner_id", guest_claims)

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
                # update channel interest date on first call participant
                BusResult(self.chat, "mail.record/insert"),
                BusResult(
                    # update new message separator (message_post)
                    self.user_employee,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_employee_in_chat,
                                message_unread_counter=0,
                                message_unread_counter_bus_id=0,
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
                            self._res_for_user(self.user_employee, internal=True),
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
                            self._res_for_user(self.user_employee, internal=True),
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
                            self._res_for_user(self.test_user, internal=True),
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
                # update channel interest date on first call participant
                BusResult(self.channel_group_a, "mail.record/insert"),
                BusResult(
                    self.user_employee,
                    # Update of the author's member record after posting the call message.
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            self._res_for_member(
                                self.member_of_employee_in_group_a,
                                message_unread_counter=0,
                                message_unread_counter_bus_id=0,
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
                            self._res_for_user(self.user_employee, internal=True),
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
                            self._res_for_user(self.user_employee, internal=True),
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
                            self._res_for_user(self.test_user, internal=True),
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
                            self._res_for_user(self.test_user, internal=True),
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
                            self._res_for_user(self.test_user, internal=True),
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
                            self._res_for_user(self.test_user, internal=True),
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
                            self._res_for_user(self.test_user, internal=True),
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
                            self._res_for_user(self.user_employee, internal=True),
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
                            self._res_for_user(self.test_user, internal=True),
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
            res["agent_ids"] = []
            res["user_ids"] = partner.user_ids.ids
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

    def _res_for_user(self, user, internal=False):
        res = {
            "all_employee_ids": [],
            "should_display_in_call_im_status": False,
            "id": user.id,
            "partner_id": user.partner_id.id,
        }
        if internal:
            res["im_status"] = user.im_status
            res["im_status_access_token"] = user._get_im_status_access_token()
        return res
