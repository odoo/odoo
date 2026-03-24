# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo import fields
from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.tests.common import HttpCase, new_test_user, tagged, users
from odoo.tools.misc import mute_logger


@tagged("RTC")
class TestChannelRTC(MailCommon, HttpCase):

    @users('employee')
    @mute_logger('odoo.models.unlink')
    @freeze_time("2023-03-15 12:34:56")
    def test_01_join_call(self):
        """Join call should remove existing sessions, remove invitation, create a new session, and return data."""
        self.maxDiff = None
        channel = self.env['discuss.channel']._create_channel(name='Test Channel', group_id=self.env.ref('base.group_user').id)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        last_rtc_session_id = channel_member.rtc_session_ids.id
        partner_data = {
            "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
            "id": channel_member.partner_id.id,
            "im_status": channel_member.partner_id.im_status,
            "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
            "main_user_id": self.user_employee.id,
            "mention_token": channel_member.partner_id._get_mention_token(),
            "name": channel_member.partner_id.name,
            "write_date": fields.Datetime.to_string(channel_member.partner_id.write_date),
        }
        member_data = {
            "channel_id": channel.id,
            "id": channel_member.id,
            "partner_id": channel_member.partner_id.id,
        }

        def notifications():
            message = self.env["mail.message"].search(
                [
                    ("model", "=", "discuss.channel"),
                    ("res_id", "=", channel.id),
                    ("message_type", "=", "notification"),
                ],
                order="id desc",
                limit=1,
            )
            return [
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": last_rtc_session_id},
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 0.0,
                                "end_dt": "2023-03-15 12:34:56",
                                "id": channel.call_history_ids.filtered("end_dt").sorted("id")[-1].id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("DELETE", [last_rtc_session_id])],
                            },
                        ],
                    },
                ),
                BusResult(
                    self.user_employee,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                **member_data,
                                "new_message_separator": channel_member.new_message_separator,
                            },
                        ],
                    },
                ),
                BusResult(channel, "discuss.channel/new_message"),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [last_rtc_session_id + 1])],
                            },
                        ],
                        "discuss.channel.member": [member_data],
                        "discuss.channel.rtc.session": [
                            {"channel_member_id": channel_member.id, "id": last_rtc_session_id + 1},
                        ],
                        "mail.message": [
                            {
                                "call_history_ids": [message.call_history_ids.id],
                                "id": message.id,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(partner_data),
                        "res.users": self._filter_users_fields(
                            {
                                "id": self.user_employee.id,
                                "employee_ids": [],
                                "partner_id": self.partner_employee.id,
                            },
                        ),
                    },
                ),
            ]

        with self.assertBus(notifications):
            store = Store()
            channel_member._rtc_join_call(store)
            res = store.get_result()
        self.assertEqual(
            res,
            {
                "discuss.channel": [
                    {
                        "id": channel.id,
                        "rtc_session_ids": [
                            ("ADD", [last_rtc_session_id + 1]),
                            ("DELETE", [last_rtc_session_id]),
                        ],
                    },
                ],
                "discuss.channel.member": [member_data],
                "discuss.channel.rtc.session": [
                    {"channel_member_id": channel_member.id, "id": last_rtc_session_id + 1},
                ],
                "res.partner": self._filter_partners_fields(partner_data),
                "res.users": self._filter_users_fields(
                    {
                        "id": self.user_employee.id,
                        "employee_ids": [],
                        "partner_id": self.partner_employee.id,
                    },
                ),
                "Rtc": {
                    "iceServers": False,
                    "localSession": last_rtc_session_id + 1,
                    "serverInfo": None,
                },
            },
        )

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_10_start_call_in_chat_should_invite_all_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        channel = self.env['discuss.channel']._get_or_create_chat(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        channel_member._rtc_join_call()
        last_rtc_session_id = channel_member.rtc_session_ids.id
        channel_member._rtc_leave_call()

        def notifications():
            message = self.env["mail.message"].search(
                [
                    ("model", "=", "discuss.channel"),
                    ("res_id", "=", channel.id),
                    ("message_type", "=", "notification"),
                ],
                order="id desc",
                limit=1,
            )
            return [
                BusResult(
                    # update new message separator (message_post)
                    self.user_employee,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member.id,
                                "new_message_separator": channel_member.new_message_separator,
                                "partner_id": channel_member.partner_id.id,
                            },
                        ],
                    },
                ),
                BusResult(channel, "discuss.channel/new_message"),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [last_rtc_session_id + 1])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id + 1,
                            },
                        ],
                        "mail.message": [
                            {
                                "call_history_ids": [message.call_history_ids.id],
                                "id": message.id,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "main_user_id": self.user_employee.id,
                                "mention_token": channel_member.partner_id._get_mention_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": self.user_employee.id,
                                "partner_id": self.partner_employee.id,
                            },
                        ),
                    },
                ),
                BusResult(
                    # incoming invitation
                    test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": last_rtc_session_id + 1,
                            },
                            {
                                "channel_id": channel.id,
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id + 1,
                                "is_camera_on": False,
                                "is_deaf": False,
                                "is_muted": False,
                                "is_screen_sharing_on": False,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "main_user_id": self.user_employee.id,
                                "mention_token": channel_member.partner_id._get_mention_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "employee_ids": [],
                                "id": self.user_employee.id,
                                "partner_id": self.user_employee.partner_id.id,
                            },
                        ),
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("ADD", [channel_member_test_user.id])],
                            }
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "main_user_id": test_user.id,
                                "mention_token": channel_member_test_user.partner_id._get_mention_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": test_user.id,
                                "partner_id": test_user.partner_id.id,
                            },
                        ),
                    },
                ),
            ]

        with self.assertBus(notifications):
            now = fields.Datetime.now()
            with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(seconds=5)):
                channel_member._rtc_join_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_11_start_call_in_group_should_invite_all_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        self.env["mail.presence"]._update_presence(test_guest)
        channel = self.env['discuss.channel']._create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel._add_members(guests=test_guest)
        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        last_rtc_session_id = channel_member.rtc_session_ids.id
        channel_member._rtc_leave_call()

        def notifications():
            message = self.env["mail.message"].search(
                [
                    ("model", "=", "discuss.channel"),
                    ("res_id", "=", channel.id),
                    ("message_type", "=", "notification"),
                ],
                order="id desc",
                limit=1,
            )
            return [
                BusResult(
                    self.user_employee,
                    # Update of the author's member record after posting the call message.
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member.id,
                                "new_message_separator": channel_member.new_message_separator,
                                "partner_id": channel_member.partner_id.id,
                            },
                        ],
                    },
                ),
                BusResult(channel, "discuss.channel/new_message"),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [last_rtc_session_id + 1])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id + 1,
                            },
                        ],
                        "mail.message": [
                            {
                                "call_history_ids": [message.call_history_ids.id],
                                "id": message.id,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "main_user_id": self.user_employee.id,
                                "mention_token": channel_member.partner_id._get_mention_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": self.user_employee.id,
                                "partner_id": self.partner_employee.id,
                            },
                        ),
                    },
                ),
                BusResult(
                    # incoming invitation
                    test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": last_rtc_session_id + 1,
                            },
                            {
                                "channel_id": channel.id,
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id + 1,
                                "is_camera_on": False,
                                "is_deaf": False,
                                "is_muted": False,
                                "is_screen_sharing_on": False,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "main_user_id": self.user_employee.id,
                                "mention_token": channel_member.partner_id._get_mention_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "employee_ids": [],
                                "id": self.user_employee.id,
                                "partner_id": self.user_employee.partner_id.id,
                            },
                        ),
                    },
                ),
                BusResult(
                    # incoming invitation
                    test_guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "id": channel_member_test_guest.id,
                                "rtc_inviting_session_id": last_rtc_session_id + 1,
                            },
                            {
                                "channel_id": channel.id,
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id + 1,
                                "is_camera_on": False,
                                "is_deaf": False,
                                "is_muted": False,
                                "is_screen_sharing_on": False,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "main_user_id": self.user_employee.id,
                                "mention_token": channel_member.partner_id._get_mention_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": self.user_employee.id,
                                "partner_id": self.user_employee.partner_id.id,
                            },
                        ),
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [
                                    (
                                        "ADD",
                                        [channel_member_test_user.id, channel_member_test_guest.id],
                                    )
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                            },
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                            },
                        ],
                        "mail.guest": [
                            {
                                "avatar_128_access_token": channel_member_test_guest.guest_id._get_avatar_128_access_token(),
                                "id": channel_member_test_guest.guest_id.id,
                                "im_status": channel_member_test_guest.guest_id.im_status,
                                "im_status_access_token": channel_member_test_guest.guest_id._get_im_status_access_token(),
                                "name": channel_member_test_guest.guest_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_guest.guest_id.write_date
                                ),
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "main_user_id": test_user.id,
                                "mention_token": channel_member_test_user.partner_id._get_mention_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": test_user.id,
                                "partner_id": test_user.partner_id.id,
                            },
                        ),
                    },
                ),
            ]

        with self.assertBus(notifications):
            now = fields.Datetime.now()
            with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(seconds=5)):
                channel_member._rtc_join_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_20_join_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        self.env["mail.presence"]._update_presence(test_guest)
        channel = self.env['discuss.channel']._create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel._add_members(guests=test_guest)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        last_rtc_session_id = channel_member.rtc_session_ids.id
        with self.assertBus(
            [
                BusResult(
                    test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("DELETE", [channel_member_test_user.id])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "main_user_id": test_user.id,
                                "mention_token": channel_member_test_user.partner_id._get_mention_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": test_user.id,
                                "partner_id": test_user.partner_id.id,
                            },
                        ),
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [last_rtc_session_id + 1])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member_test_user.id,
                                "id": last_rtc_session_id + 1,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "main_user_id": test_user.id,
                                "mention_token": channel_member_test_user.partner_id._get_mention_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": test_user.id,
                                "partner_id": test_user.partner_id.id,
                            },
                        ),
                    },
                ),
            ],
        ):
            channel_member_test_user._rtc_join_call()

        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        with self.assertBus(
            [
                BusResult(
                    test_guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "id": channel_member_test_guest.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("DELETE", [channel_member_test_guest.id])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                            },
                        ],
                        "mail.guest": [
                            {
                                "avatar_128_access_token": channel_member_test_guest.guest_id._get_avatar_128_access_token(),
                                "id": channel_member_test_guest.guest_id.id,
                                "im_status": channel_member_test_guest.guest_id.im_status,
                                "im_status_access_token": channel_member_test_guest.guest_id._get_im_status_access_token(),
                                "name": channel_member_test_guest.guest_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_guest.guest_id.write_date
                                ),
                            },
                        ],
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [last_rtc_session_id + 2])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member_test_guest.id,
                                "id": last_rtc_session_id + 2,
                            },
                        ],
                        "mail.guest": [
                            {
                                "avatar_128_access_token": channel_member_test_guest.guest_id._get_avatar_128_access_token(),
                                "id": channel_member_test_guest.guest_id.id,
                                "im_status": channel_member_test_guest.guest_id.im_status,
                                "im_status_access_token": channel_member_test_guest.guest_id._get_im_status_access_token(),
                                "name": channel_member_test_guest.guest_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_guest.guest_id.write_date
                                ),
                            },
                        ],
                    },
                ),
            ],
        ):
            channel_member_test_guest._rtc_join_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_21_leave_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        self.env["mail.presence"]._update_presence(test_guest)
        channel = self.env['discuss.channel']._create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel._add_members(guests=test_guest)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()

        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        with self.assertBus(
            [
                BusResult(
                    test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("DELETE", [channel_member_test_user.id])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "main_user_id": test_user.id,
                                "mention_token": channel_member_test_user.partner_id._get_mention_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": test_user.id,
                                "partner_id": test_user.partner_id.id,
                            },
                        ),
                    },
                ),
            ],
        ):
            channel_member_test_user._rtc_leave_call()

        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        with self.assertBus(
            [
                BusResult(
                    test_guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "id": channel_member_test_guest.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("DELETE", [channel_member_test_guest.id])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                            },
                        ],
                        "mail.guest": [
                            {
                                "avatar_128_access_token": channel_member_test_guest.guest_id._get_avatar_128_access_token(),
                                "id": channel_member_test_guest.guest_id.id,
                                "im_status": channel_member_test_guest.guest_id.im_status,
                                "im_status_access_token": channel_member_test_guest.guest_id._get_im_status_access_token(),
                                "name": channel_member_test_guest.guest_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_guest.guest_id.write_date
                                ),
                            },
                        ],
                    },
                ),
            ],
        ):
            channel_member_test_guest._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    @freeze_time("2023-03-15 12:34:56")
    def test_25_lone_call_participant_leaving_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        self.env["mail.presence"]._update_presence(test_guest)
        channel = self.env['discuss.channel']._create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel._add_members(guests=test_guest)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        channel_member._rtc_join_call()
        last_rtc_session_id = channel_member.rtc_session_ids.id
        with self.assertBus(
            [
                BusResult(
                    test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                ),
                BusResult(
                    test_guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "id": channel_member_test_guest.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [
                                    (
                                        "DELETE",
                                        [channel_member_test_user.id, channel_member_test_guest.id],
                                    )
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                            },
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                            },
                        ],
                        "mail.guest": [
                            {
                                "avatar_128_access_token": channel_member_test_guest.guest_id._get_avatar_128_access_token(),
                                "id": channel_member_test_guest.guest_id.id,
                                "im_status": channel_member_test_guest.guest_id.im_status,
                                "im_status_access_token": channel_member_test_guest.guest_id._get_im_status_access_token(),
                                "name": channel_member_test_guest.guest_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_guest.guest_id.write_date
                                ),
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "main_user_id": test_user.id,
                                "mention_token": channel_member_test_user.partner_id._get_mention_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": test_user.id,
                                "partner_id": test_user.partner_id.id,
                            },
                        ),
                    },
                ),
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": last_rtc_session_id},
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 0.0,
                                "end_dt": "2023-03-15 12:34:56",
                                "id": channel.call_history_ids.id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("DELETE", [last_rtc_session_id])],
                            },
                        ],
                    },
                ),
            ],
        ):
            channel_member._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_30_add_members_while_in_call_should_invite_new_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        self.env["mail.presence"]._update_presence(test_guest)
        channel = self.env['discuss.channel']._create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda member: member.partner_id == self.user_employee.partner_id)
        now = fields.Datetime.now()
        with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(seconds=5)):
            channel_member._rtc_join_call()

        def notifications():
            channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda member: member.partner_id == test_user.partner_id)
            channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda member: member.guest_id == test_guest)
            last_rtc_session_id = channel_member.rtc_session_ids.id
            return [
                BusResult(channel, "mail.record/insert"),  # discuss.channel (channel_name_member_ids)
                BusResult(test_user, "discuss.channel/joined"),
                BusResult(self.user_employee, "mail.record/insert"),  # discuss.channel.member (message_unread_counter, new_message_separator, …)
                BusResult(channel, "discuss.channel/new_message"),
                BusResult(test_guest, "discuss.channel/joined"),
                BusResult(self.user_employee, "mail.record/insert"),  # discuss.channel.member (message_unread_counter, new_message_separator, …)
                BusResult(channel, "discuss.channel/new_message"),
                BusResult(channel, "mail.record/insert"),  # discuss.channel (member_count), discuss.channel.member
                BusResult(
                    test_user,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": channel_member_test_user.rtc_inviting_session_id.id,
                            },
                            {
                                "channel_id": channel.id,
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id,
                                "is_camera_on": channel_member.rtc_session_ids.is_camera_on,
                                "is_deaf": channel_member.rtc_session_ids.is_deaf,
                                "is_muted": channel_member.rtc_session_ids.is_muted,
                                "is_screen_sharing_on": channel_member.rtc_session_ids.is_screen_sharing_on,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "main_user_id": self.user_employee.id,
                                "mention_token": channel_member.partner_id._get_mention_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": self.user_employee.id,
                                "employee_ids": [],
                                "partner_id": self.partner_employee.id,
                            },
                        ),
                    },
                ),
                BusResult(
                    test_guest,
                    "mail.record/insert",
                    {
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "id": channel_member_test_guest.id,
                                "rtc_inviting_session_id": channel_member_test_guest.rtc_inviting_session_id.id,
                            },
                            {
                                "channel_id": channel.id,
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id,
                                "is_camera_on": channel_member.rtc_session_ids.is_camera_on,
                                "is_deaf": channel_member.rtc_session_ids.is_deaf,
                                "is_muted": channel_member.rtc_session_ids.is_muted,
                                "is_screen_sharing_on": channel_member.rtc_session_ids.is_screen_sharing_on,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "main_user_id": self.user_employee.id,
                                "mention_token": channel_member.partner_id._get_mention_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": self.user_employee.id,
                                "partner_id": self.user_employee.partner_id.id,
                            },
                        ),
                    },
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [
                                    (
                                        "ADD",
                                        [channel_member_test_user.id, channel_member_test_guest.id],
                                    )
                                ],
                            }
                        ],
                        "discuss.channel.member": [
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                            },
                            {
                                "channel_id": channel.id,
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                            },
                        ],
                        "mail.guest": [
                            {
                                "avatar_128_access_token": channel_member_test_guest.guest_id._get_avatar_128_access_token(),
                                "id": channel_member_test_guest.guest_id.id,
                                "im_status": channel_member_test_guest.guest_id.im_status,
                                "im_status_access_token": channel_member_test_guest.guest_id._get_im_status_access_token(),
                                "name": channel_member_test_guest.guest_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_guest.guest_id.write_date
                                ),
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "main_user_id": test_user.id,
                                "mention_token": channel_member_test_user.partner_id._get_mention_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                        "res.users": self._filter_users_fields(
                            {
                                "id": test_user.id,
                                "partner_id": test_user.partner_id.id,
                            },
                        ),
                    },
                ),
            ]

        with self.assertBus(notifications):
            with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(seconds=10)):
                channel._add_members(users=test_user, guests=test_guest, invite_to_rtc_call=True)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    @freeze_time("2023-03-15 12:34:56")
    def test_40_leave_call_should_remove_existing_sessions_of_user_in_channel_and_return_data(self):
        self.maxDiff = None
        channel = self.env['discuss.channel']._create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        last_rtc_session_id = channel_member.rtc_session_ids.id
        with self.assertBus(
            [
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": last_rtc_session_id},
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 1.0,
                                "end_dt": "2023-03-15 13:34:56",
                                "id": channel.call_history_ids.id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [["DELETE", [last_rtc_session_id]]],
                            },
                        ],
                    },
                ),
            ],
        ):
            now = fields.Datetime.now()
            with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(hours=1)):
                channel_member._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    @freeze_time("2023-03-15 12:34:56")
    def test_50_garbage_collect_should_remove_old_sessions_and_notify_data(self):
        self.env["discuss.channel.rtc.session"].sudo().search([]).unlink()  # clean up before test
        channel = self.env['discuss.channel']._create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        channel_member.rtc_session_ids.flush_model()
        channel_member.rtc_session_ids._write({'write_date': fields.Datetime.now() - relativedelta(days=2)})
        last_rtc_session_id = channel_member.rtc_session_ids.id
        with self.assertBus(
            [
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": last_rtc_session_id},
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 0.0,
                                "end_dt": "2023-03-15 12:34:56",
                                "id": channel.call_history_ids.id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("DELETE", [last_rtc_session_id])],
                            },
                        ],
                    },
                ),
            ],
        ):
            self.env['discuss.channel.rtc.session'].sudo()._gc_inactive_sessions()
        self.assertFalse(channel_member.rtc_session_ids)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    @freeze_time("2023-03-15 12:34:56")
    def test_51_action_disconnect_should_remove_selected_session_and_notify_data(self):
        channel = self.env['discuss.channel']._create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        last_rtc_session_id = channel_member.rtc_session_ids.id
        with self.assertBus(
            [
                BusResult(
                    self.user_employee,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": last_rtc_session_id},
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "duration_hour": 0.0,
                                "end_dt": "2023-03-15 12:34:56",
                                "id": channel.call_history_ids.id,
                            },
                        ],
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("DELETE", [last_rtc_session_id])],
                            },
                        ],
                    },
                ),
            ],
        ):
            channel_member.rtc_session_ids.action_disconnect()
        self.assertFalse(channel_member.rtc_session_ids)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_60_rtc_sync_sessions_should_gc_and_return_outdated_and_active_sessions(self):
        channel = self.env['discuss.channel']._create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        store = Store()
        channel_member._rtc_join_call(store)
        join_call_values = store.get_result()
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        test_channel_member = self.env['discuss.channel.member'].create({
            'guest_id': test_guest.id,
            'channel_id': channel.id,
        })
        test_session = self.env['discuss.channel.rtc.session'].sudo().create({'channel_member_id': test_channel_member.id})
        test_session.flush_model()
        test_session._write({'write_date': fields.Datetime.now() - relativedelta(days=2)})
        unused_ids = [9998, 9999]
        with self.assertBus(
            [
                BusResult(
                    test_guest,
                    "discuss.channel.rtc.session/ended",
                    {"sessionId": test_session.id},
                ),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [
                            {"id": channel.id, "rtc_session_ids": [("DELETE", [test_session.id])]},
                        ],
                    },
                ),
            ],
        ):
            current_rtc_sessions, outdated_rtc_sessions = channel_member._rtc_sync_sessions(
                check_rtc_session_ids=[join_call_values["Rtc"]["localSession"]] + unused_ids
            )
        self.assertEqual(channel_member.rtc_session_ids, current_rtc_sessions)
        self.assertEqual(unused_ids, outdated_rtc_sessions.ids)
        self.assertFalse(outdated_rtc_sessions.exists())

    def test_07_call_invitation_ui(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        john = new_test_user(self.env, "john", groups="base.group_user", email="john@test.com")
        channel = self.env["discuss.channel"].with_user(bob)._create_group(partners_to=(bob | john).partner_id.ids)
        channel.with_user(bob).self_member_id.sudo()._rtc_join_call()
        self._reset_bus()
        self.start_tour("/odoo", "discuss_call_invitation.js", login="john")
