# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo import fields
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.tests.common import tagged, users
from odoo.tools.misc import mute_logger


@tagged("RTC", "post_install", "-at_install")
class TestChannelRTC(MailCommon):

    @users('employee')
    @mute_logger('odoo.models.unlink')
    @freeze_time("2023-03-15 12:34:56")
    def test_01_join_call(self):
        """Join call should remove existing sessions, remove invitation, create a new session, and return data."""
        self.maxDiff = None
        channel = self.env['discuss.channel']._create_channel(name='Test Channel', group_id=self.env.ref('base.group_user').id)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        with self.assertBus(
            [
                # delete of old sessions
                (self.cr.dbname, "discuss.channel", channel.id),
                # end of old sessions
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # update history with duration of previous session
                (self.cr.dbname, "discuss.channel", channel.id),
                # insert new session
                (self.cr.dbname, "discuss.channel", channel.id),
                # message unread counter (message post)
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # start call notification message post
                (self.cr.dbname, "discuss.channel", channel.id),
                # new call history (not asserted below)
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "discuss.channel.rtc.session/ended",
                    "payload": {"sessionId": channel_member.rtc_session_ids.id},
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("DELETE", [channel_member.rtc_session_ids.id])],
                            },
                        ],
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [channel_member.rtc_session_ids.id + 1])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                                "channel_id": {
                                    "id": channel_member.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": channel_member.rtc_session_ids.id + 1,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "id": channel_member.id,
                                "new_message_separator": channel_member.new_message_separator + 1,
                                "partner_id": channel_member.partner_id.id,
                                "channel_id": {"id": channel.id, "model": "discuss.channel"}
                            }
                        ]
                    },
                },
            ],
        ):
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
                            ("ADD", [channel_member.rtc_session_ids.id]),
                            ("DELETE", [channel_member.rtc_session_ids.id - 1]),
                        ],
                    },
                ],
                "discuss.channel.member": [
                    {
                        "id": channel_member.id,
                        "partner_id": channel_member.partner_id.id,
                        "channel_id": {
                            "id": channel_member.channel_id.id,
                            "model": "discuss.channel",
                        },
                    },
                ],
                "discuss.channel.rtc.session": [
                    {
                        "channel_member_id": channel_member.id,
                        "id": channel_member.rtc_session_ids.id,
                    },
                ],
                "res.partner": self._filter_partners_fields(
                    {
                        "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                        "id": channel_member.partner_id.id,
                        "im_status": channel_member.partner_id.im_status,
                        "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                        "name": channel_member.partner_id.name,
                        "write_date": fields.Datetime.to_string(
                            channel_member.partner_id.write_date
                        ),
                    },
                ),
                "Rtc": {
                    "iceServers": False,
                    "localSession": channel_member.rtc_session_ids.id,
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

        with self.assertBus(
            [
                # update new session
                (self.cr.dbname, "discuss.channel", channel.id),
                # message_post "started a live conference" (not asserted below)
                (self.cr.dbname, "discuss.channel", channel.id),
                # update new message separator
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # update of last interest (not asserted below)
                (self.cr.dbname, "discuss.channel", channel.id),
                # update call history (not asserted below)
                (self.cr.dbname, "discuss.channel", channel.id),
                # incoming invitation
                (self.cr.dbname, "res.partner", test_user.partner_id.id),
                # update list of invitations
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [last_rtc_session_id + 1])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                                "channel_id": {
                                    "id": channel_member.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id + 1,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("ADD", [channel_member_test_user.id])],
                            }
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "channel_id": {
                                    "id": channel_member_test_user.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
            ],
        ):
            now = fields.Datetime.now()
            with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(seconds=5)):
                channel_member._rtc_join_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_11_start_call_in_group_should_invite_all_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel']._create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel._add_members(guests=test_guest)
        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        last_rtc_session_id = channel_member.rtc_session_ids.id
        channel_member._rtc_leave_call()

        with self.assertBus(
            [
                # update new session
                (self.cr.dbname, "discuss.channel", channel.id),
                # message_post "started a live conference" (not asserted below)
                (self.cr.dbname, "discuss.channel", channel.id),
                # update new message separator
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # update of last interest (not asserted below)
                (self.cr.dbname, "discuss.channel", channel.id),
                # update call history (not asserted below)
                (self.cr.dbname, "discuss.channel", channel.id),
                # incoming invitation
                (self.cr.dbname, "res.partner", test_user.partner_id.id),
                # incoming invitation
                (self.cr.dbname, "mail.guest", test_guest.id),
                # update list of invitations
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [last_rtc_session_id + 1])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                                "channel_id": {
                                    "id": channel_member.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id + 1,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token":  channel_member.partner_id._get_im_status_access_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [last_rtc_session_id + 1])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                                "channel_id": {
                                    "id": channel_member.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": last_rtc_session_id + 1,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member.partner_id._get_avatar_128_access_token(),
                                "id": channel_member.partner_id.id,
                                "im_status": channel_member.partner_id.im_status,
                                "im_status_access_token": channel_member.partner_id._get_im_status_access_token(),
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
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
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "channel_id": {
                                    "id": channel_member_test_user.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                            {
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "channel_id": {
                                    "id": channel_member_test_guest.channel_id.id,
                                    "model": "discuss.channel",
                                },
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
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
            ],
        ):
            now = fields.Datetime.now()
            with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(seconds=5)):
                channel_member._rtc_join_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_20_join_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel']._create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel._add_members(guests=test_guest)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()

        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        with self.assertBus(
            [
                # update invitation
                (self.cr.dbname, "res.partner", test_user.partner_id.id),
                # update list of invitations
                (self.cr.dbname, "discuss.channel", channel.id),
                # update sessions
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "channel_id": {"id": channel.id, "model": "discuss.channel"},
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("DELETE", [channel_member_test_user.id])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "channel_id": {
                                    "id": channel_member_test_user.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("ADD", [channel_member.rtc_session_ids.id + 1])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "channel_id": {
                                    "id": channel_member_test_user.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member_test_user.id,
                                "id": channel_member.rtc_session_ids.id + 1,
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
            ],
        ):
            channel_member_test_user._rtc_join_call()

        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        with self.assertBus(
            [
                # update invitation
                (self.cr.dbname, "mail.guest", test_guest.id),
                # update list of invitations
                (self.cr.dbname, "discuss.channel", channel.id),
                # update sessions
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "channel_id": {"id": channel.id, "model": "discuss.channel"},
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "id": channel_member_test_guest.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("DELETE", [channel_member_test_guest.id])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "channel_id": {
                                    "id": channel_member_test_guest.channel_id.id,
                                    "model": "discuss.channel",
                                },
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
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [
                                    ("ADD", [channel_member.rtc_session_ids.id + 2])
                                ],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "channel_id": {
                                    "id": channel_member_test_guest.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member_test_guest.id,
                                "id": channel_member.rtc_session_ids.id + 2,
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
                },
            ],
        ):
            channel_member_test_guest._rtc_join_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_21_leave_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel']._create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel._add_members(guests=test_guest)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()

        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        with self.assertBus(
            [
                # update invitation
                (self.cr.dbname, "res.partner", test_user.partner_id.id),
                # update list of invitations
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "channel_id": {"id": channel.id, "model": "discuss.channel"},
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("DELETE", [channel_member_test_user.id])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "channel_id": {
                                    "id": channel_member_test_user.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "res.partner": self._filter_partners_fields(
                            {
                                "avatar_128_access_token": channel_member_test_user.partner_id._get_avatar_128_access_token(),
                                "id": channel_member_test_user.partner_id.id,
                                "im_status": channel_member_test_user.partner_id.im_status,
                                "im_status_access_token": channel_member_test_user.partner_id._get_im_status_access_token(),
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
            ],
        ):
            channel_member_test_user._rtc_leave_call()

        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        with self.assertBus(
            [
                # update invitation
                (self.cr.dbname, "mail.guest", test_guest.id),
                # update list of invitations
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "channel_id": {"id": channel.id, "model": "discuss.channel"},
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "id": channel_member_test_guest.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "invited_member_ids": [("DELETE", [channel_member_test_guest.id])],
                            },
                        ],
                        "discuss.channel.member": [
                            {
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "channel_id": {
                                    "id": channel_member_test_guest.channel_id.id,
                                    "model": "discuss.channel",
                                },
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
                },
            ],
        ):
            channel_member_test_guest._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_25_lone_call_participant_leaving_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel']._create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel._add_members(guests=test_guest)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        channel_member._rtc_join_call()

        with self.assertBus(
            [
                # update invitation
                (self.cr.dbname, "res.partner", test_user.partner_id.id),
                # update invitation
                (self.cr.dbname, "mail.guest", test_guest.id),
                # update list of invitations
                (self.cr.dbname, "discuss.channel", channel.id),
                # update sessions
                (self.cr.dbname, "discuss.channel", channel.id),
                # end session
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # update call history (not asserted below)
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "discuss.channel.rtc.session/ended",
                    "payload": {"sessionId": channel_member.rtc_session_ids.id},
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "channel_id": {"id": channel.id, "model": "discuss.channel"},
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "channel_id": {"id": channel.id, "model": "discuss.channel"},
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "id": channel_member_test_guest.id,
                                "rtc_inviting_session_id": False,
                            },
                        ],
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
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
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "channel_id": {
                                    "id": channel_member_test_user.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                            {
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "channel_id": {
                                    "id": channel_member_test_guest.channel_id.id,
                                    "model": "discuss.channel",
                                },
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
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("DELETE", [channel_member.rtc_session_ids.id])],
                            },
                        ],
                    },
                },
            ],
        ):
            channel_member._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_30_add_members_while_in_call_should_invite_new_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel']._create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda member: member.partner_id == self.user_employee.partner_id)
        now = fields.Datetime.now()
        with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(seconds=5)):
            channel_member._rtc_join_call()
        self._reset_bus()

        with self.mock_bus():
            with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(seconds=10)):
                channel._add_members(users=test_user, guests=test_guest, invite_to_rtc_call=True)

        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda member: member.partner_id == test_user.partner_id)
        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda member: member.guest_id == test_guest)
        found_bus_notifs = self.assertBusNotifications(
            [
                # mail.record/insert - discuss.channel (channel_name_member_ids)
                (self.cr.dbname, "discuss.channel", channel.id),
                # discuss.channel/joined
                (self.cr.dbname, "res.partner", test_user.partner_id.id),
                # mail.record/insert - discuss.channel (last_interest_dt)
                (self.cr.dbname, "discuss.channel", channel.id),
                # mail.record/insert - discuss.channel.member (message_unread_counter, new_message_separator, …)
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # discuss.channel/new_message
                (self.cr.dbname, "discuss.channel", channel.id),
                # discuss.channel/joined
                (self.cr.dbname, "mail.guest", test_guest.id),
                # mail.record/insert - discuss.channel.member (message_unread_counter, new_message_separator, …)
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # discuss.channel/new_message
                (self.cr.dbname, "discuss.channel", channel.id),
                # mail.record/insert - discuss.channel (member_count), discuss.channel.member
                (self.cr.dbname, "discuss.channel", channel.id),
                # mail.record/insert - discuss.channel.member (rtc_inviting_session_id)
                (self.cr.dbname, "res.partner", test_user.partner_id.id),
                # mail.record/insert - discuss.channel.member (rtc_inviting_session_id)
                (self.cr.dbname, "mail.guest", test_guest.id),
                # mail.record/insert - discuss.channel (invited_member_ids), discuss.channel.member
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            message_items=[
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "channel_id": {
                                    "id": channel_member_test_user.channel_id.id,
                                    "model": "discuss.channel",
                                },
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "rtc_inviting_session_id": channel_member_test_user.rtc_inviting_session_id.id,
                            },
                            {
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                                "channel_id": {
                                    "id": channel_member.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": channel_member.rtc_session_ids.id,
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
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel.member": [
                            {
                                "channel_id": {
                                    "id": channel_member_test_guest.channel_id.id,
                                    "model": "discuss.channel",
                                },
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "id": channel_member_test_guest.id,
                                "rtc_inviting_session_id": channel_member_test_guest.rtc_inviting_session_id.id,
                            },
                            {
                                "id": channel_member.id,
                                "partner_id": channel_member.partner_id.id,
                                "channel_id": {
                                    "id": channel_member.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                        "discuss.channel.rtc.session": [
                            {
                                "channel_member_id": channel_member.id,
                                "id": channel_member.rtc_session_ids.id,
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
                                "name": channel_member.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
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
                                "id": channel_member_test_user.id,
                                "partner_id": channel_member_test_user.partner_id.id,
                                "channel_id": {
                                    "id": channel_member_test_user.channel_id.id,
                                    "model": "discuss.channel",
                                },
                            },
                            {
                                "id": channel_member_test_guest.id,
                                "guest_id": channel_member_test_guest.guest_id.id,
                                "channel_id": {
                                    "id": channel_member_test_guest.channel_id.id,
                                    "model": "discuss.channel",
                                },
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
                                "name": channel_member_test_user.partner_id.name,
                                "write_date": fields.Datetime.to_string(
                                    channel_member_test_user.partner_id.write_date
                                ),
                            },
                        ),
                    },
                },
            ],
        )
        self.assertEqual(self._new_bus_notifs, found_bus_notifs)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_40_leave_call_should_remove_existing_sessions_of_user_in_channel_and_return_data(self):
        channel = self.env['discuss.channel']._create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        with self.assertBus(
            [
                # update list of sessions
                (self.cr.dbname, "discuss.channel", channel.id),
                # end session
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # update call history (not asserted below)
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "discuss.channel.rtc.session/ended",
                    "payload": {"sessionId": channel_member.rtc_session_ids.id},
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("DELETE", [channel_member.rtc_session_ids.id])],
                            },
                        ],
                    },
                },
            ],
        ):
            now = fields.Datetime.now()
            with patch.object(fields.Datetime, 'now', lambda: now + relativedelta(seconds=5)):
                channel_member._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_50_garbage_collect_should_remove_old_sessions_and_notify_data(self):
        self.env["discuss.channel.rtc.session"].sudo().search([]).unlink()  # clean up before test
        channel = self.env['discuss.channel']._create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        channel_member.rtc_session_ids.flush_model()
        channel_member.rtc_session_ids._write({'write_date': fields.Datetime.now() - relativedelta(days=2)})
        with self.assertBus(
            [
                # update list of sessions
                (self.cr.dbname, "discuss.channel", channel.id),
                # session ended
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # update call history duration
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "discuss.channel.rtc.session/ended",
                    "payload": {"sessionId": channel_member.rtc_session_ids.id},
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("DELETE", [channel_member.rtc_session_ids.id])],
                            },
                        ],
                    },
                },
            ],
        ):
            self.env['discuss.channel.rtc.session'].sudo()._gc_inactive_sessions()
        self.assertFalse(channel_member.rtc_session_ids)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_51_action_disconnect_should_remove_selected_session_and_notify_data(self):
        channel = self.env['discuss.channel']._create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        with self.assertBus(
            [
                # update list of sessions
                (self.cr.dbname, "discuss.channel", channel.id),
                # session ended
                (self.cr.dbname, "res.partner", self.user_employee.partner_id.id),
                # update call history duration
                (self.cr.dbname, "discuss.channel", channel.id),
            ],
            [
                {
                    "type": "discuss.channel.rtc.session/ended",
                    "payload": {"sessionId": channel_member.rtc_session_ids.id},
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {
                                "id": channel.id,
                                "rtc_session_ids": [("DELETE", [channel_member.rtc_session_ids.id])],
                            },
                        ],
                    },
                },
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
                # update list of sessions
                (self.cr.dbname, "discuss.channel", channel.id),
                # session ended
                (self.cr.dbname, "mail.guest", test_guest.id),
            ],
            [
                {
                    "type": "discuss.channel.rtc.session/ended",
                    "payload": {"sessionId": test_session.id},
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [
                            {"id": channel.id, "rtc_session_ids": [("DELETE", [test_session.id])]},
                        ],
                    },
                },
            ],
        ):
            current_rtc_sessions, outdated_rtc_sessions = channel_member._rtc_sync_sessions(
                check_rtc_session_ids=[join_call_values["Rtc"]["localSession"]] + unused_ids
            )
        self.assertEqual(channel_member.rtc_session_ids, current_rtc_sessions)
        self.assertEqual(unused_ids, outdated_rtc_sessions.ids)
        self.assertFalse(outdated_rtc_sessions.exists())
