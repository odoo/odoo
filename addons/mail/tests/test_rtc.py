# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


@tagged('RTC')
class TestChannelInternals(MailCommon):

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_01_join_call(self):
        """Join call should remove existing sessions, remove invitation, create a new session, and return data."""
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='Test Channel')['id'])
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # end of previous session
                (self.cr.dbname, 'mail.channel', channel.id),  # update sessions
                (self.cr.dbname, 'mail.channel', channel.id),  # update sessions
            ],
            [
                {
                    'type': 'mail.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_partner.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert-and-unlink', [{'id': channel_partner.rtc_session_ids.id}])],
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert', [{
                            'id': channel_partner.rtc_session_ids.id + 1,
                            'isCameraOn': False,
                            'isDeaf': False,
                            'isMuted': False,
                            'isScreenSharingOn': False,
                            'partner': [('insert', {
                                'id': self.user_employee.partner_id.id,
                                'name': "Ernest Employee",
                            })],
                        }])],
                    },
                },
            ]
        ):
            res = channel_partner._rtc_join_call()
        self.assertEqual(res, {
            'iceServers': False,
            'rtcSessions': [
                ('insert', [{
                    'id': channel_partner.rtc_session_ids.id,
                    'isCameraOn': False,
                    'isDeaf': False,
                    'isMuted': False,
                    'isScreenSharingOn': False,
                    'partner': [('insert', {
                        'id': self.user_employee.partner_id.id,
                        'name': "Ernest Employee",
                    })],
                }]),
                ('insert-and-unlink', [{'id': channel_partner.rtc_session_ids.id - 1}]),
            ],
            'sessionId': channel_partner.rtc_session_ids.id,
        })

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_10_start_call_in_chat_should_invite_all_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].channel_get(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)['id'])
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()
        last_rtc_session_id = channel_partner.rtc_session_ids.id
        channel_partner._rtc_leave_call()

        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'mail.channel', channel.id),  # update new session
                (self.cr.dbname, 'mail.channel', channel.id),  # message_post "started a live conference" (not asserted below)
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # incoming invitation
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of invitations
            ],
            [
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert', [{
                            'id': last_rtc_session_id + 1,
                            'isCameraOn': False,
                            'isDeaf': False,
                            'isMuted': False,
                            'isScreenSharingOn': False,
                            'partner': [('insert', {
                                'id': self.user_employee.partner_id.id,
                                'name': "Ernest Employee",
                            })],
                        }])],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'invitedPartners': [('insert', [{'id': test_user.partner_id.id, 'name': 'Test User'}])],
                    },
                },
            ]
        ):
            res = channel_partner._rtc_join_call()
        self.assertNotIn('invitedGuests', res)
        self.assertIn('invitedPartners', res)
        self.assertEqual(res['invitedPartners'], [('insert', [{'id': test_user.partner_id.id, 'name': "Test User"}])])

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_11_start_call_in_group_should_invite_all_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)['id'])
        channel.add_members(guest_ids=test_guest.ids)
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()
        last_rtc_session_id = channel_partner.rtc_session_ids.id
        channel_partner._rtc_leave_call()

        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'mail.channel', channel.id),  # update new session
                (self.cr.dbname, 'mail.channel', channel.id),  # message_post "started a live conference" (not asserted below)
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # incoming invitation
                (self.cr.dbname, 'mail.guest', test_guest.id),  # incoming invitation
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of invitations
            ],
            [
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert', [{
                            'id': last_rtc_session_id + 1,
                            'isCameraOn': False,
                            'isDeaf': False,
                            'isMuted': False,
                            'isScreenSharingOn': False,
                            'partner': [('insert', {
                                'id': self.user_employee.partner_id.id,
                                'name': "Ernest Employee",
                            })],
                        }])],
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert', [{
                            'id': last_rtc_session_id + 1,
                            'isCameraOn': False,
                            'isDeaf': False,
                            'isMuted': False,
                            'isScreenSharingOn': False,
                            'partner': [('insert', {
                                'id': self.user_employee.partner_id.id,
                                'name': "Ernest Employee",
                            })],
                        }])],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'invitedGuests': [('insert', [{'id': test_guest.id, 'name': 'Test Guest'}])],
                        'invitedPartners': [('insert', [{'id': test_user.partner_id.id, 'name': 'Test User'}])],
                    },
                },
            ]
        ):
            res = channel_partner._rtc_join_call()
        self.assertIn('invitedGuests', res)
        self.assertEqual(res['invitedGuests'], [('insert', [{'id': test_guest.id, 'name': 'Test Guest'}])])
        self.assertIn('invitedPartners', res)
        self.assertEqual(res['invitedPartners'], [('insert', [{'id': test_user.partner_id.id, 'name': "Test User"}])])

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_20_join_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)['id'])
        channel.add_members(guest_ids=test_guest.ids)
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()

        channel_partner_test_user = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == test_user.partner_id)
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update invitation
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of invitations
                (self.cr.dbname, 'mail.channel', channel.id),  # update sessions
            ],
            [
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'rtcInvitingSession': [('unlink',)],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'invitedPartners': [('insert-and-unlink', [{'id': test_user.partner_id.id}])],
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert', [
                            {
                                'id': channel_partner.rtc_session_ids.id + 1,
                                'isCameraOn': False,
                                'isDeaf': False,
                                'isMuted': False,
                                'isScreenSharingOn': False,
                                'partner': [('insert', {
                                    'id': test_user.partner_id.id,
                                    'name': 'Test User',
                                })],
                            },
                        ])],
                    },
                },
            ]
        ):
            channel_partner_test_user._rtc_join_call()

        channel_partner_test_guest = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.guest_id == test_guest)
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'mail.guest', test_guest.id),  # update invitation
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of invitations
                (self.cr.dbname, 'mail.channel', channel.id),  # update sessions
            ],
            [
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'rtcInvitingSession': [('unlink',)],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'invitedGuests': [('insert-and-unlink', [{'id': test_guest.id}])],
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert', [
                            {
                                'id': channel_partner.rtc_session_ids.id + 2,
                                'isCameraOn': False,
                                'isDeaf': False,
                                'isMuted': False,
                                'isScreenSharingOn': False,
                                'guest': [('insert', {
                                    'id': test_guest.id,
                                    'name': 'Test Guest',
                                })],
                            },
                        ])],
                    },
                },
            ]
        ):
            channel_partner_test_guest._rtc_join_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_21_leave_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)['id'])
        channel.add_members(guest_ids=test_guest.ids)
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()

        channel_partner_test_user = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == test_user.partner_id)
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update invitation
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of invitations
            ],
            [
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'rtcInvitingSession': [('unlink',)],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'invitedPartners': [('insert-and-unlink', [{'id': test_user.partner_id.id}])],
                    },
                },
            ]
        ):
            channel_partner_test_user._rtc_leave_call()

        channel_partner_test_guest = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.guest_id == test_guest)
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'mail.guest', test_guest.id),  # update invitation
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of invitations
            ],
            [
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'rtcInvitingSession': [('unlink',)],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'invitedGuests': [('insert-and-unlink', [{'id': test_guest.id}])],
                    },
                },
            ]
        ):
            channel_partner_test_guest._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_25_lone_call_participant_leaving_call_should_cancel_pending_invitations(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=(self.user_employee.partner_id + test_user.partner_id).ids)['id'])
        channel.add_members(guest_ids=test_guest.ids)
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()

        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # end session
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update invitation
                (self.cr.dbname, 'mail.guest', test_guest.id),  # update invitation
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of invitations
                (self.cr.dbname, 'mail.channel', channel.id),  # update sessions
            ],
            [
                {
                    'type': 'mail.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_partner.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'rtcInvitingSession': [('unlink',)],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'rtcInvitingSession': [('unlink',)],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'invitedGuests': [('insert-and-unlink', [{'id': test_guest.id}])],
                        'invitedPartners': [('insert-and-unlink', [{'id': test_user.partner_id.id}])],
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert-and-unlink', [{'id': channel_partner.rtc_session_ids.id}])],
                    },
                },
            ]
        ):
            channel_partner._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_30_add_members_while_in_call_should_invite_new_members_to_call(self):
        test_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=self.user_employee.partner_id.ids)['id'])
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # channel joined (not asserted below)
                (self.cr.dbname, 'mail.channel', channel.id),  # message_post "invited" (not asserted below)
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'mail.channel', channel.id),  # new members (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # incoming invitation
                (self.cr.dbname, 'mail.guest', test_guest.id),  # incoming invitation
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of invitations
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'res.partner', test_user.partner_id.id),  # update of last interest (not asserted below)
                (self.cr.dbname, 'mail.channel', channel.id),  # new member (guest) (not asserted below)
                (self.cr.dbname, 'mail.guest', test_guest.id), # channel joined for guest (not asserted below)
            ],
            [
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'rtcInvitingSession': [('insert', {
                            'id': channel_partner.rtc_session_ids.id,
                            'isCameraOn': False,
                            'isDeaf': False,
                            'isMuted': False,
                            'isScreenSharingOn': False,
                            'partner': [('insert', {
                                'id': self.user_employee.partner_id.id,
                                'name': "Ernest Employee",
                            })],
                        })],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'rtcInvitingSession': [('insert', {
                            'id': channel_partner.rtc_session_ids.id,
                            'isCameraOn': False,
                            'isDeaf': False,
                            'isMuted': False,
                            'isScreenSharingOn': False,
                            'partner': [('insert', {
                                'id': self.user_employee.partner_id.id,
                                'name': "Ernest Employee",
                            })],
                        })],
                    },
                },
                {
                    'type': 'mail.channel/insert',
                    'payload': {
                        'id': channel.id,
                        'invitedGuests': [('insert', [{'id': test_guest.id, 'name': 'Test Guest'}])],
                        'invitedPartners': [('insert', [{'id': test_user.partner_id.id, 'name': 'Test User'}])],
                    },
                },
            ],
        ):
            channel.add_members(partner_ids=test_user.partner_id.ids, guest_ids=test_guest.ids, invite_to_rtc_call=True)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_40_leave_call_should_remove_existing_sessions_of_user_in_channel_and_return_data(self):
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=self.user_employee.partner_id.ids)['id'])
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # end session
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of sessions
            ],
            [
                {
                    'type': 'mail.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_partner.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert-and-unlink', [{'id': channel_partner.rtc_session_ids.id}])],
                    },
                },
            ],
        ):
            channel_partner._rtc_leave_call()

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_50_garbage_collect_should_remove_old_sessions_and_notify_data(self):
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=self.user_employee.partner_id.ids)['id'])
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()
        channel_partner.rtc_session_ids.flush()
        channel_partner.rtc_session_ids._write({'write_date': fields.Datetime.now() - relativedelta(days=2)})
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # session ended
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of sessions
            ],
            [
                {
                    'type': 'mail.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_partner.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert-and-unlink', [{'id': channel_partner.rtc_session_ids.id}])],
                    },
                },
            ],
        ):
            self.env['mail.channel.rtc.session'].sudo()._gc_inactive_sessions()
        self.assertFalse(channel_partner.rtc_session_ids)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_51_action_disconnect_should_remove_selected_session_and_notify_data(self):
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=self.user_employee.partner_id.ids)['id'])
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        channel_partner._rtc_join_call()
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'res.partner', self.user_employee.partner_id.id),  # session ended
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of sessions
            ],
            [
                {
                    'type': 'mail.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': channel_partner.rtc_session_ids.id,
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert-and-unlink', [{'id': channel_partner.rtc_session_ids.id}])],
                    },
                },
            ],
        ):
            channel_partner.rtc_session_ids.action_disconnect()
        self.assertFalse(channel_partner.rtc_session_ids)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_60_rtc_sync_sessions_should_gc_and_return_outdated_and_active_sessions(self):
        channel = self.env['mail.channel'].browse(self.env['mail.channel'].create_group(partners_to=self.user_employee.partner_id.ids)['id'])
        channel_partner = channel.sudo().channel_last_seen_partner_ids.filtered(lambda channel_partner: channel_partner.partner_id == self.user_employee.partner_id)
        join_call_values = channel_partner._rtc_join_call()
        test_guest = self.env['mail.guest'].sudo().create({'name': "Test Guest"})
        test_channel_partner = self.env['mail.channel.partner'].create({
            'guest_id': test_guest.id,
            'channel_id': channel.id,
        })
        test_session = self.env['mail.channel.rtc.session'].sudo().create({'channel_partner_id': test_channel_partner.id})
        test_session.flush()
        test_session._write({'write_date': fields.Datetime.now() - relativedelta(days=2)})
        unused_ids = [9998, 9999]
        self.env['bus.bus'].sudo().search([]).unlink()
        with self.assertBus(
            [
                (self.cr.dbname, 'mail.guest', test_guest.id),  # session ended
                (self.cr.dbname, 'mail.channel', channel.id),  # update list of sessions
            ],
            [
                {
                    'type': 'mail.channel.rtc.session/ended',
                    'payload': {
                        'sessionId': test_session.id,
                    },
                },
                {
                    'type': 'mail.channel/rtc_sessions_update',
                    'payload': {
                        'id': channel.id,
                        'rtcSessions': [('insert-and-unlink', [{'id': test_session.id}])],
                    },
                },
            ],
        ):
            current_rtc_sessions, outdated_rtc_sessions = channel_partner._rtc_sync_sessions(check_rtc_session_ids=[join_call_values['sessionId']] + unused_ids)
        self.assertEqual(channel_partner.rtc_session_ids, current_rtc_sessions)
        self.assertEqual(unused_ids, outdated_rtc_sessions.ids)
        self.assertFalse(outdated_rtc_sessions.exists())
