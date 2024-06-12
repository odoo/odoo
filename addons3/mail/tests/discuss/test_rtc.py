# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged("RTC", "post_install", "-at_install")
class TestChannelRTC(MailCommon):

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_01_join_call(self):
        """Join call should remove existing sessions, remove invitation, create a new session, and return data."""
        channel = self.env['discuss.channel'].channel_create(name='Test Channel', group_id=self.env.ref('base.group_user').id)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # end of previous session
                (self.cr.dbname, 'discuss.channel', channel.id),  # update sessions
                (self.cr.dbname, 'discuss.channel', channel.id),  # update sessions
            ],
            [
                {
                    'type': 'discuss.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_member.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('DELETE', [{'id': channel_member.rtc_session_ids.id}])],
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('ADD', [{
                            'id': channel_member.rtc_session_ids.id + 1,
                            'channelMember': {
                                "id": channel_member.id,
                                "thread": {"id": channel_member.channel_id.id, "model": "discuss.channel"},
                                "persona": {
                                    "id": channel_member.partner_id.id,
                                    "name": channel_member.partner_id.name,
                                    "im_status": channel_member.partner_id.im_status,
                                    "type": "partner",
                                },
                            },
                        }])],
                    },
                },
            ]
        ):
            res = channel_member._rtc_join_call()
        self.assertEqual(res, {
            'iceServers': False,
            'rtcSessions': [
                ('ADD', [{
                    'id': channel_member.rtc_session_ids.id,
                    'channelMember': {
                        "id": channel_member.id,
                        "thread": {"id": channel_member.channel_id.id, "model": "discuss.channel"},
                        "persona": {
                            "id": channel_member.partner_id.id,
                            "name": channel_member.partner_id.name,
                            "im_status": channel_member.partner_id.im_status,
                            "type": "partner",
                        },
                    },
                }]),
                ('DELETE', [{'id': channel_member.rtc_session_ids.id - 1}]),
            ],
            'sessionId': channel_member.rtc_session_ids.id,
            'serverInfo': None,
        })

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_10_start_call_in_chat_should_invite_all_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        channel = self.env['discuss.channel'].channel_get(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        channel_member._rtc_join_call()
        last_rtc_session_id = channel_member.rtc_session_ids.id
        channel_member._rtc_leave_call()

        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'discuss.channel', channel.id),  # update new session
                (self.cr.dbname, 'discuss.channel', channel.id),  # channel_seen basic infos after posting join message
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # channel seen member infos (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # message_post "started a live conference" (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id, "members"),  # update of pin state (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # incoming invitation
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of invitations
            ],
            [
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('ADD', [{
                            'id': last_rtc_session_id + 1,
                            'channelMember': {
                                "id": channel_member.id,
                                "thread": {"id": channel_member.channel_id.id, "model": "discuss.channel"},
                                "persona": {
                                    "id": channel_member.partner_id.id,
                                    "name": channel_member.partner_id.name,
                                    "im_status": channel_member.partner_id.im_status,
                                    "type": "partner",
                                },
                            },
                        }])],
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'invitedMembers': [('ADD', [{
                                'id': channel_member_test_user.id,
                                'thread': {'id': channel_member_test_user.channel_id.id, 'model': "discuss.channel"},
                                'persona': {
                                    'id': channel_member_test_user.partner_id.id,
                                    'name': channel_member_test_user.partner_id.name,
                                    'im_status': channel_member_test_user.partner_id.im_status,
                                    'type': "partner",
                                },
                            }])],
                        }
                    },
                },
            ]
        ):
            res = channel_member._rtc_join_call()
        self.assertIn('invitedMembers', res)
        self.assertEqual(res['invitedMembers'], [('ADD', [{
            'id': channel_member_test_user.id,
            'thread': {'id': channel_member_test_user.channel_id.id, 'model': "discuss.channel"},
            'persona': {
                'id': channel_member_test_user.partner_id.id,
                'name': channel_member_test_user.partner_id.name,
                'im_status': channel_member_test_user.partner_id.im_status,
                'type': "partner",
            },
        }])])

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_11_start_call_in_group_should_invite_all_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel'].create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel.add_members(guest_ids=test_guest.ids)
        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        last_rtc_session_id = channel_member.rtc_session_ids.id
        channel_member._rtc_leave_call()

        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'discuss.channel', channel.id),  # update new session
                (self.cr.dbname, 'discuss.channel', channel.id),  # channel_seen basic infos after posting join message
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # channel seen member info (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # message_post "started a live conference" (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id, "members"),  # update of pin state (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # incoming invitation
                (self.cr.dbname, 'mail.guest', test_guest.id),  # incoming invitation
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of invitations
            ],
            [
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('ADD', [{
                            'id': last_rtc_session_id + 1,
                            'channelMember': {
                                "id": channel_member.id,
                                "thread": {"id": channel_member.channel_id.id, "model": "discuss.channel"},
                                "persona": {
                                    "id": channel_member.partner_id.id,
                                    "name": channel_member.partner_id.name,
                                    "im_status": channel_member.partner_id.im_status,
                                    "type": "partner",
                                },
                            },
                        }])],
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('ADD', [{
                            'id': last_rtc_session_id + 1,
                            'channelMember': {
                                "id": channel_member.id,
                                "thread": {"id": channel_member.channel_id.id, "model": "discuss.channel"},
                                "persona": {
                                    "id": channel_member.partner_id.id,
                                    "name": channel_member.partner_id.name,
                                    "im_status": channel_member.partner_id.im_status,
                                    "type": "partner",
                                },
                            },
                        }])],
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'invitedMembers': [('ADD', [
                                {
                                    'id': channel_member_test_user.id,
                                    'thread': {'id': channel_member_test_user.channel_id.id, 'model': "discuss.channel"},
                                    'persona': {
                                        'id': channel_member_test_user.partner_id.id,
                                        'name': channel_member_test_user.partner_id.name,
                                        'im_status': channel_member_test_user.partner_id.im_status,
                                        'type': "partner",
                                    },
                                },
                                {
                                    'id': channel_member_test_guest.id,
                                    'thread': {'id': channel_member_test_guest.channel_id.id, 'model': "discuss.channel"},
                                    'persona': {
                                        'id': channel_member_test_guest.guest_id.id,
                                        'name': channel_member_test_guest.guest_id.name,
                                        'im_status': channel_member_test_guest.guest_id.im_status,
                                        'type': "guest",
                                    },
                                },
                            ])],
                        }
                    },
                },
            ]
        ):
            res = channel_member._rtc_join_call()
        self.assertIn('invitedMembers', res)
        self.assertEqual(res['invitedMembers'], [('ADD', [
            {
                'id': channel_member_test_user.id,
                'thread': {'id': channel_member_test_user.channel_id.id, 'model': "discuss.channel"},
                'persona': {
                    'id': channel_member_test_user.partner_id.id,
                    'name': channel_member_test_user.partner_id.name,
                    'im_status': channel_member_test_user.partner_id.im_status,
                    'type': "partner",
                },
            },
            {
                'id': channel_member_test_guest.id,
                'thread': {'id': channel_member_test_guest.channel_id.id, 'model': "discuss.channel"},
                'persona': {
                    'id': channel_member_test_guest.guest_id.id,
                    'name': channel_member_test_guest.guest_id.name,
                    'im_status': channel_member_test_guest.guest_id.im_status,
                    'type': "guest",
                },
            },
        ])])

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_20_join_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel'].create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel.add_members(guest_ids=test_guest.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()

        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update invitation
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of invitations
                (self.cr.dbname, 'discuss.channel', channel.id),  # update sessions
            ],
            [
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'rtcInvitingSession': False,
                        }
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'invitedMembers': [('DELETE', [{
                                'id': channel_member_test_user.id,
                                'thread': {'id': channel_member_test_user.channel_id.id, 'model': "discuss.channel"},
                                'persona': {
                                    'id': channel_member_test_user.partner_id.id,
                                    'name': channel_member_test_user.partner_id.name,
                                    'im_status': channel_member_test_user.partner_id.im_status,
                                    'type': "partner",
                                },
                            }])],
                        }
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('ADD', [
                            {
                                'id': channel_member.rtc_session_ids.id + 1,
                                'channelMember': {
                                    "id": channel_member_test_user.id,
                                    "thread": {"id": channel_member_test_user.channel_id.id, "model": "discuss.channel"},
                                    "persona": {
                                        "id": channel_member_test_user.partner_id.id,
                                        "name": channel_member_test_user.partner_id.name,
                                        "im_status": channel_member_test_user.partner_id.im_status,
                                        "type": "partner",
                                    },
                                },
                            },
                        ])],
                    },
                },
            ]
        ):
            channel_member_test_user._rtc_join_call()

        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'mail.guest', test_guest.id),  # update invitation
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of invitations
                (self.cr.dbname, 'discuss.channel', channel.id),  # update sessions
            ],
            [
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'rtcInvitingSession': False,
                        }
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'invitedMembers': [('DELETE', [{
                                'id': channel_member_test_guest.id,
                                'thread': {'id': channel_member_test_guest.channel_id.id, 'model': "discuss.channel"},
                                'persona': {
                                    'id': channel_member_test_guest.guest_id.id,
                                    'name': channel_member_test_guest.guest_id.name,
                                    'im_status': channel_member_test_guest.guest_id.im_status,
                                    'type': "guest",
                                },
                            }])],
                        }
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('ADD', [
                            {
                                'id': channel_member.rtc_session_ids.id + 2,
                                'channelMember': {
                                    "id": channel_member_test_guest.id,
                                    "thread": {"id": channel_member_test_guest.channel_id.id, "model": "discuss.channel"},
                                    "persona": {
                                        "id": channel_member_test_guest.guest_id.id,
                                        "name": channel_member_test_guest.guest_id.name,
                                        'im_status': channel_member_test_guest.guest_id.im_status,
                                        "type": "guest",
                                    },
                                },
                            },
                        ])],
                    },
                },
            ]
        ):
            channel_member_test_guest._rtc_join_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_21_leave_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel'].create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel.add_members(guest_ids=test_guest.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()

        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update invitation
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of invitations
            ],
            [
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'rtcInvitingSession': False,
                        }
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'invitedMembers': [('DELETE', [{
                                'id': channel_member_test_user.id,
                                'thread': {'id': channel_member_test_user.channel_id.id, 'model': "discuss.channel"},
                                'persona': {
                                    'id': channel_member_test_user.partner_id.id,
                                    'name': channel_member_test_user.partner_id.name,
                                    'im_status': channel_member_test_user.partner_id.im_status,
                                    'type': "partner",
                                },
                            }])],
                        }
                    },
                },
            ]
        ):
            channel_member_test_user._rtc_leave_call()

        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'mail.guest', test_guest.id),  # update invitation
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of invitations
            ],
            [
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'rtcInvitingSession': False,
                        }
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'invitedMembers': [('DELETE', [{
                                'id': channel_member_test_guest.id,
                                'thread': {'id': channel_member_test_guest.channel_id.id, 'model': "discuss.channel"},
                                'persona': {
                                    'id': channel_member_test_guest.guest_id.id,
                                    'name': channel_member_test_guest.guest_id.name,
                                    'im_status': channel_member_test_guest.guest_id.im_status,
                                    'type': "guest",
                                },
                            }])],
                        }
                    },
                },
            ]
        ):
            channel_member_test_guest._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_25_lone_call_participant_leaving_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel'].create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)
        channel.add_members(guest_ids=test_guest.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == test_user.partner_id)
        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.guest_id == test_guest)
        channel_member._rtc_join_call()

        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # end session
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update invitation
                (self.cr.dbname, 'mail.guest', test_guest.id),  # update invitation
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of invitations
                (self.cr.dbname, 'discuss.channel', channel.id),  # update sessions
            ],
            [
                {
                    'type': 'discuss.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_member.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'rtcInvitingSession': False,
                        }
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'rtcInvitingSession': False,
                        }
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'invitedMembers': [('DELETE', [
                                {
                                    'id': channel_member_test_user.id,
                                    'thread': {'id': channel_member_test_user.channel_id.id, 'model': "discuss.channel"},
                                    'persona': {
                                        'id': channel_member_test_user.partner_id.id,
                                        'name': channel_member_test_user.partner_id.name,
                                        'im_status': channel_member_test_user.partner_id.im_status,
                                        'type': "partner",
                                    },
                                },
                                {
                                    'id': channel_member_test_guest.id,
                                    'thread': {'id': channel_member_test_guest.channel_id.id, 'model': "discuss.channel"},
                                    'persona': {
                                        'id': channel_member_test_guest.guest_id.id,
                                        'name': channel_member_test_guest.guest_id.name,
                                        'im_status': channel_member_test_guest.guest_id.im_status,
                                        'type': "guest",
                                    },
                                },
                            ])],
                        }
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('DELETE', [{'id': channel_member.rtc_session_ids.id}])],
                    },
                },
            ]
        ):
            channel_member._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_30_add_members_while_in_call_should_invite_new_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['discuss.channel'].create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda member: member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        self.env['bus.bus'].sudo().search([]).unlink()

        with self.mock_bus():
            channel.add_members(partner_ids=test_user.partner_id.ids, guest_ids=test_guest.ids, invite_to_rtc_call=True)

        channel_member_test_user = channel.sudo().channel_member_ids.filtered(lambda member: member.partner_id == test_user.partner_id)
        channel_member_test_guest = channel.sudo().channel_member_ids.filtered(lambda member: member.guest_id == test_guest)
        found_bus_notifs = self.assertBusNotifications(
            [
                (self.cr.dbname, 'discuss.channel', channel.id),  # channel joined -- seen (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # channel joined  -- last_interrest (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # message_post -- new_message (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # message_post -- seen basic infos (not asserted below)
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # message post -- seen member infos (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id, "members"),  # update of pin state (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # message_post -- last_interrest (not asserted below)
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # message post -- seen member infos (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # new members (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # incoming invitation
                (self.cr.dbname, 'mail.guest', test_guest.id),  # incoming invitation
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of invitations
                (self.cr.dbname, 'discuss.channel', channel.id, "members"),  # update of pin state (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'discuss.channel', channel.id),  # new member (guest) (not asserted below)
                (self.cr.dbname, 'mail.guest', test_guest.id),  # channel joined for guest (not asserted below)
            ],
            message_items=[
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'rtcInvitingSession': {
                                'id': channel_member.rtc_session_ids.id,
                                'channelMember': {
                                    "id": channel_member.id,
                                    "thread": {"id": channel_member.channel_id.id, "model": "discuss.channel"},
                                    "persona": {
                                        "id": channel_member.partner_id.id,
                                        "name": channel_member.partner_id.name,
                                        "im_status": channel_member.partner_id.im_status,
                                        "type": "partner",
                                    },
                                },
                            },
                        }
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'rtcInvitingSession': {
                                'id': channel_member.rtc_session_ids.id,
                                'channelMember': {
                                    "id": channel_member.id,
                                    "thread": {"id": channel_member.channel_id.id, "model": "discuss.channel"},
                                    "persona": {
                                        "id": channel_member.partner_id.id,
                                        "name": channel_member.partner_id.name,
                                        "im_status": channel_member.partner_id.im_status,
                                        "type": "partner",
                                    },
                                },
                            },
                        }
                    },
                },
                {
                    'type': 'mail.record/insert',
                    'payload': {
                        'Thread': {
                            'id': channel.id,
                            'model': 'discuss.channel',
                            'invitedMembers': [('ADD', [
                                {
                                    'id': channel_member_test_user.id,
                                    'thread': {'id': channel_member_test_user.channel_id.id, 'model': "discuss.channel"},
                                    'persona': {
                                        'id': channel_member_test_user.partner_id.id,
                                        'name': channel_member_test_user.partner_id.name,
                                        'im_status': channel_member_test_user.partner_id.im_status,
                                        'type': "partner",
                                    },
                                },
                                {
                                    'id': channel_member_test_guest.id,
                                    'thread': {'id': channel_member_test_guest.channel_id.id, 'model': "discuss.channel"},
                                    'persona': {
                                        'id': channel_member_test_guest.guest_id.id,
                                        'name': channel_member_test_guest.guest_id.name,
                                        'im_status': channel_member_test_guest.guest_id.im_status,
                                        'type': "guest",
                                    },
                                },
                            ])],
                        }
                    },
                },
            ],
        )
        self.assertEqual(self._new_bus_notifs, found_bus_notifs)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_40_leave_call_should_remove_existing_sessions_of_user_in_channel_and_return_data(self):
        channel = self.env['discuss.channel'].create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # end session
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of sessions
            ],
            [
                {
                    'type': 'discuss.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_member.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('DELETE', [{'id': channel_member.rtc_session_ids.id}])],
                    },
                },
            ],
        ):
            channel_member._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_50_garbage_collect_should_remove_old_sessions_and_notify_data(self):
        channel = self.env['discuss.channel'].create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        channel_member.rtc_session_ids.flush_model()
        channel_member.rtc_session_ids._write({'write_date': fields.Datetime.now() - relativedelta(days=2)})
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # session ended
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of sessions
            ],
            [
                {
                    'type': 'discuss.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_member.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('DELETE', [{'id': channel_member.rtc_session_ids.id}])],
                    },
                },
            ],
        ):
            self.env['discuss.channel.rtc.session'].sudo()._gc_inactive_sessions()
        self.assertFalse(channel_member.rtc_session_ids)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_51_action_disconnect_should_remove_selected_session_and_notify_data(self):
        channel = self.env['discuss.channel'].create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        channel_member._rtc_join_call()
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # session ended
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of sessions
            ],
            [
                {
                    'type': 'discuss.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_member.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('DELETE', [{'id': channel_member.rtc_session_ids.id}])],
                    },
                },
            ],
        ):
            channel_member.rtc_session_ids.action_disconnect()
        self.assertFalse(channel_member.rtc_session_ids)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_60_rtc_sync_sessions_should_gc_and_return_outdated_and_active_sessions(self):
        channel = self.env['discuss.channel'].create_group(partners_to=self.user_employee.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(lambda channel_member: channel_member.partner_id == self.user_employee.partner_id)
        join_call_values = channel_member._rtc_join_call()
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        test_channel_member = self.env['discuss.channel.member'].create({
            'guest_id': test_guest.id,
            'channel_id': channel.id,
        })
        test_session = self.env['discuss.channel.rtc.session'].sudo().create({'channel_member_id': test_channel_member.id})
        test_session.flush_model()
        test_session._write({'write_date': fields.Datetime.now() - relativedelta(days=2)})
        unused_ids = [9998, 9999]
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'mail.guest', test_guest.id),  # session ended
                (self.cr.dbname, 'discuss.channel', channel.id),  # update list of sessions
            ],
            [
                {
                    'type': 'discuss.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': test_session.id,
                    },
                },
                {
                    'type': 'discuss.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('DELETE', [{'id': test_session.id}])],
                    },
                },
            ],
        ):
            current_rtc_sessions, outdated_rtc_sessions = channel_member._rtc_sync_sessions(check_rtc_session_ids=[join_call_values['sessionId']] + unused_ids)
        self.assertEqual(channel_member.rtc_session_ids, current_rtc_sessions)
        self.assertEqual(unused_ids, outdated_rtc_sessions.ids)
        self.assertFalse(outdated_rtc_sessions.exists())
