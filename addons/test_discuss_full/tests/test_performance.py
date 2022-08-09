# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.tests.common import users, tagged, TransactionCase, warmup
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


@tagged('post_install', '-at_install')
class TestDiscussFullPerformance(TransactionCase):
    def setUp(self):
        super().setUp()
        self.group_user = self.env.ref('base.group_user')
        self.users = self.env['res.users'].create([
            {
                'email': 'e.e@example.com',
                'groups_id': [Command.link(self.group_user.id)],
                'login': 'emp',
                'name': 'Ernest Employee',
                'notification_type': 'inbox',
                'odoobot_state': 'disabled',
                'signature': '--\nErnest',
            },
            {'name': 'test1', 'login': 'test1', 'email': 'test1@example.com'},
            {'name': 'test2', 'login': 'test2', 'email': 'test2@example.com'},
            {'name': 'test3', 'login': 'test3'},
            {'name': 'test4', 'login': 'test4'},
            {'name': 'test5', 'login': 'test5'},
            {'name': 'test6', 'login': 'test6'},
            {'name': 'test7', 'login': 'test7'},
            {'name': 'test8', 'login': 'test8'},
            {'name': 'test9', 'login': 'test9'},
            {'name': 'test10', 'login': 'test10'},
            {'name': 'test11', 'login': 'test11'},
            {'name': 'test12', 'login': 'test12'},
            {'name': 'test13', 'login': 'test13'},
            {'name': 'test14', 'login': 'test14'},
            {'name': 'test15', 'login': 'test15'},
        ])
        self.employees = self.env['hr.employee'].create([{
            'user_id': user.id,
        } for user in self.users])
        self.leave_type = self.env['hr.leave.type'].create({
            'requires_allocation': 'no',
            'name': 'Legal Leaves',
            'time_type': 'leave',
        })
        self.leaves = self.env['hr.leave'].create([{
            'date_from': date.today() + relativedelta(days=-2),
            'date_to': date.today() + relativedelta(days=2),
            'employee_id': employee.id,
            'holiday_status_id': self.leave_type.id,
        } for employee in self.employees])

    @users('emp')
    @warmup
    def test_init_messaging(self):
        """Test performance of `_init_messaging`."""
        self.channel_general = self.env.ref('mail.channel_all_employees')  # Unfortunately #general cannot be deleted. Assertions below assume data from a fresh db with demo.
        self.env['mail.channel'].sudo().search([('id', '!=', self.channel_general.id)]).unlink()
        self.user_root = self.env.ref('base.user_root')
        # create public channels
        self.channel_channel_public_1 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='public 1', privacy='public')['id'])
        self.channel_channel_public_1.add_members((self.users[0] + self.users[2] + self.users[3] + self.users[4] + self.users[8]).partner_id.ids)
        self.channel_channel_public_2 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='public 2', privacy='public')['id'])
        self.channel_channel_public_2.add_members((self.users[0] + self.users[2] + self.users[4] + self.users[7] + self.users[9]).partner_id.ids)
        # create groups channels
        self.channel_channel_group_1 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='group 1', privacy='groups')['id'])
        self.channel_channel_group_1.add_members((self.users[0] + self.users[2] + self.users[3] + self.users[6] + self.users[12]).partner_id.ids)
        self.channel_channel_group_2 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='group 2', privacy='groups')['id'])
        self.channel_channel_group_2.add_members((self.users[0] + self.users[2] + self.users[6] + self.users[7] + self.users[13]).partner_id.ids)
        # create private channels
        self.channel_channel_private_1 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='private 1', privacy='private')['id'])
        self.channel_channel_private_1.add_members((self.users[0] + self.users[2] + self.users[3] + self.users[5] + self.users[10]).partner_id.ids)
        self.channel_channel_private_2 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_create(name='private 2', privacy='private')['id'])
        self.channel_channel_private_2.add_members((self.users[0] + self.users[2] + self.users[5] + self.users[7] + self.users[11]).partner_id.ids)
        # create chats
        self.channel_chat_1 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_get((self.users[0] + self.users[14]).partner_id.ids)['id'])
        self.channel_chat_2 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_get((self.users[0] + self.users[15]).partner_id.ids)['id'])
        self.channel_chat_3 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_get((self.users[0] + self.users[2]).partner_id.ids)['id'])
        self.channel_chat_4 = self.env['mail.channel'].browse(self.env['mail.channel'].channel_get((self.users[0] + self.users[3]).partner_id.ids)['id'])
        # create groups
        self.channel_group_1 = self.env['mail.channel'].browse(self.env['mail.channel'].create_group((self.users[0] + self.users[12]).partner_id.ids)['id'])
        # create livechats
        im_livechat_channel = self.env['im_livechat.channel'].sudo().create({'name': 'support', 'user_ids': [Command.link(self.users[0].id)]})
        self.users[0].im_status = 'online'  # make available for livechat (ignore leave)
        self.channel_livechat_1 = self.env['mail.channel'].browse(im_livechat_channel._open_livechat_mail_channel(anonymous_name='anon 1', previous_operator_id=self.users[0].partner_id.id, user_id=self.users[1].id, country_id=self.env.ref('base.in').id)['id'])
        self.channel_livechat_1.with_user(self.users[1]).message_post(body="test")
        self.channel_livechat_2 = self.env['mail.channel'].browse(im_livechat_channel.with_user(self.env.ref('base.public_user'))._open_livechat_mail_channel(anonymous_name='anon 2', previous_operator_id=self.users[0].partner_id.id, country_id=self.env.ref('base.be').id)['id'])
        self.channel_livechat_2.with_user(self.env.ref('base.public_user')).sudo().message_post(body="test")
        # add needaction
        self.users[0].notification_type = 'inbox'
        message = self.channel_channel_public_1.message_post(body='test', message_type='comment', author_id=self.users[2].partner_id.id, partner_ids=self.users[0].partner_id.ids)
        # add star
        message.toggle_message_starred()
        self.env.company.sudo().name = 'YourCompany'

        self.maxDiff = None
        self.env.flush_all()
        self.env.invalidate_all()
        with self.assertQueryCount(emp=self._get_query_count()):
            init_messaging = self.users[0].with_user(self.users[0])._init_messaging()

        self.assertEqual(init_messaging, self._get_init_messaging_result())

    def _get_init_messaging_result(self):
        """
            Returns the result of a call to init_messaging.

            The point of having a separate getter is to allow it to be overriden.
        """
        return {
            'needaction_inbox_counter': 1,
            'starred_counter': 1,
            'channels': [
                {
                    'authorizedGroupFullName': self.group_user.full_name,
                    'channel': {
                        'avatarCacheKey': self.channel_general._get_avatar_cache_key(),
                        'channel_type': 'channel',
                        'custom_channel_name': False,
                        'id': self.channel_general.id,
                        'memberCount': len(self.group_user.users | self.user_root),
                        'serverMessageUnreadCounter': 5,
                    },
                    'create_uid': self.user_root.id,
                    'defaultDisplayMode': False,
                    'description': 'General announcements for all employees.',
                    'group_based_subscription': True,
                    'id': self.channel_general.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_general.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': next(res['message_id'] for res in self.channel_general._channel_last_message_ids()),
                    'message_needaction_counter': 0,
                    'name': 'general',
                    'public': 'groups',
                    'rtcSessions': [('insert', [])],
                    'seen_message_id': False,
                    'state': 'open',
                    'uuid': self.channel_general.uuid,
                },
                {
                    'authorizedGroupFullName': self.group_user.full_name,
                    'channel': {
                        'avatarCacheKey': self.channel_channel_public_1._get_avatar_cache_key(),
                        'channel_type': 'channel',
                        'custom_channel_name': False,
                        'id': self.channel_channel_public_1.id,
                        'memberCount': 5,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'id': self.channel_channel_public_1.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_public_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': next(res['message_id'] for res in self.channel_channel_public_1._channel_last_message_ids()),
                    'message_needaction_counter': 1,
                    'name': 'public 1',
                    'public': 'public',
                    'rtcSessions': [('insert', [])],
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_public_1._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_public_1.uuid,
                },
                {
                    'authorizedGroupFullName': self.group_user.full_name,
                    'channel': {
                        'avatarCacheKey': self.channel_channel_public_2._get_avatar_cache_key(),
                        'channel_type': 'channel',
                        'custom_channel_name': False,
                        'id': self.channel_channel_public_2.id,
                        'memberCount': 5,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'id': self.channel_channel_public_2.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_public_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': next(res['message_id'] for res in self.channel_channel_public_2._channel_last_message_ids()),
                    'message_needaction_counter': 0,
                    'name': 'public 2',
                    'public': 'public',
                    'rtcSessions': [('insert', [])],
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_public_2._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_public_2.uuid,
                },
                {
                    'authorizedGroupFullName': self.group_user.full_name,
                    'channel': {
                        'avatarCacheKey': self.channel_channel_group_1._get_avatar_cache_key(),
                        'channel_type': 'channel',
                        'custom_channel_name': False,
                        'id': self.channel_channel_group_1.id,
                        'memberCount': 5,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'id': self.channel_channel_group_1.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_group_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': next(res['message_id'] for res in self.channel_channel_group_1._channel_last_message_ids()),
                    'message_needaction_counter': 0,
                    'name': 'group 1',
                    'public': 'groups',
                    'rtcSessions': [('insert', [])],
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_group_1._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_group_1.uuid,
                },
                {
                    'authorizedGroupFullName': self.group_user.full_name,
                    'channel': {
                        'avatarCacheKey': self.channel_channel_group_2._get_avatar_cache_key(),
                        'channel_type': 'channel',
                        'custom_channel_name': False,
                        'id': self.channel_channel_group_2.id,
                        'memberCount': 5,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'id': self.channel_channel_group_2.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_group_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': next(res['message_id'] for res in self.channel_channel_group_2._channel_last_message_ids()),
                    'message_needaction_counter': 0,
                    'name': 'group 2',
                    'public': 'groups',
                    'rtcSessions': [('insert', [])],
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_group_2._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_group_2.uuid,
                },
                {
                    'authorizedGroupFullName': self.group_user.full_name,
                    'channel': {
                        'avatarCacheKey': self.channel_channel_private_1._get_avatar_cache_key(),
                        'channel_type': 'channel',
                        'custom_channel_name': False,
                        'id': self.channel_channel_private_1.id,
                        'memberCount': 5,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'id': self.channel_channel_private_1.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_private_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': next(res['message_id'] for res in self.channel_channel_private_1._channel_last_message_ids()),
                    'message_needaction_counter': 0,
                    'name': 'private 1',
                    'public': 'private',
                    'rtcSessions': [('insert', [])],
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_private_1._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_private_1.uuid,
                },
                {
                    'authorizedGroupFullName': self.group_user.full_name,
                    'channel': {
                        'avatarCacheKey': self.channel_channel_private_2._get_avatar_cache_key(),
                        'channel_type': 'channel',
                        'custom_channel_name': False,
                        'id': self.channel_channel_private_2.id,
                        'memberCount': 5,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'id': self.channel_channel_private_2.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_private_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': next(res['message_id'] for res in self.channel_channel_private_2._channel_last_message_ids()),
                    'message_needaction_counter': 0,
                    'name': 'private 2',
                    'public': 'private',
                    'rtcSessions': [('insert', [])],
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_private_2._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_private_2.uuid,
                },
                {
                    'authorizedGroupFullName': False,
                    'channel': {
                        'avatarCacheKey': self.channel_group_1._get_avatar_cache_key(),
                        'channel_type': 'group',
                        'custom_channel_name': False,
                        'id': self.channel_group_1.id,
                        'memberCount': 2,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'guestMembers': [('insert', [])],
                    'id': self.channel_group_1.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_group_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': False,
                    'members': [
                        {
                            'active': True,
                            'display_name': 'Ernest Employee',
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'user_id': self.users[0].id,
                        },
                        {
                            'active': True,
                            'display_name': 'test12',
                            'email': False,
                            'id': self.users[12].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'test12',
                            'out_of_office_date_end': False,
                            'user_id': self.users[12].id,
                        },
                    ],
                    'message_needaction_counter': 0,
                    'name': '',
                    'public': 'private',
                    'rtcSessions': [('insert', [])],
                    'seen_message_id': False,
                    'seen_partners_info': [
                        {
                            'fetched_message_id': False,
                            'id': self.channel_group_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'partner_id': self.users[0].partner_id.id,
                            'seen_message_id': False,
                        },
                        {
                            'fetched_message_id': False,
                            'id': self.channel_group_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[12].partner_id).id,
                            'partner_id': self.users[12].partner_id.id,
                            'seen_message_id': False,
                        }
                    ],
                    'state': 'open',
                    'uuid': self.channel_group_1.uuid,
                },
                {
                    'authorizedGroupFullName': False,
                    'channel': {
                        'avatarCacheKey': self.channel_chat_1._get_avatar_cache_key(),
                        'channel_type': 'chat',
                        'custom_channel_name': False,
                        'id': self.channel_chat_1.id,
                        'memberCount': 2,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'guestMembers': [('insert', [])],
                    'id': self.channel_chat_1.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_chat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': False,
                    'members': [
                        {
                            'active': True,
                            'display_name': 'Ernest Employee',
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'user_id': self.users[0].id,
                        },
                        {
                            'active': True,
                            'display_name': 'test14',
                            'email': False,
                            'id': self.users[14].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'test14',
                            'out_of_office_date_end': False,
                            'user_id': self.users[14].id,
                        },
                    ],
                    'message_needaction_counter': 0,
                    'name': 'Ernest Employee, test14',
                    'public': 'private',
                    'rtcSessions': [('insert', [])],
                    'seen_partners_info': [
                        {
                            'fetched_message_id': False,
                            'id': self.channel_chat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'partner_id': self.users[0].partner_id.id,
                            'seen_message_id': False,
                        },
                        {
                            'fetched_message_id': False,
                            'id': self.channel_chat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[14].partner_id).id,
                            'partner_id': self.users[14].partner_id.id,
                            'seen_message_id': False,
                        },
                    ],
                    'seen_message_id': False,
                    'state': 'open',
                    'uuid': self.channel_chat_1.uuid,
                },
                {
                    'authorizedGroupFullName': False,
                    'channel': {
                        'avatarCacheKey': self.channel_chat_2._get_avatar_cache_key(),
                        'channel_type': 'chat',
                        'custom_channel_name': False,
                        'id': self.channel_chat_2.id,
                        'memberCount': 2,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'guestMembers': [('insert', [])],
                    'id': self.channel_chat_2.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_chat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': False,
                    'members': [
                        {
                            'active': True,
                            'display_name': 'Ernest Employee',
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'user_id': self.users[0].id,
                        },
                        {
                            'active': True,
                            'display_name': 'test15',
                            'email': False,
                            'id': self.users[15].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'test15',
                            'out_of_office_date_end': False,
                            'user_id': self.users[15].id,
                        },
                    ],
                    'message_needaction_counter': 0,
                    'name': 'Ernest Employee, test15',
                    'public': 'private',
                    'rtcSessions': [('insert', [])],
                    'seen_partners_info': [
                        {
                            'fetched_message_id': False,
                            'id': self.channel_chat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'partner_id': self.users[0].partner_id.id,
                            'seen_message_id': False,
                        },
                        {
                            'fetched_message_id': False,
                            'id': self.channel_chat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[15].partner_id).id,
                            'partner_id': self.users[15].partner_id.id,
                            'seen_message_id': False,
                        },
                    ],
                    'seen_message_id': False,
                    'state': 'open',
                    'uuid': self.channel_chat_2.uuid,
                },
                {
                    'authorizedGroupFullName': False,
                    'channel': {
                        'avatarCacheKey': self.channel_chat_3._get_avatar_cache_key(),
                        'channel_type': 'chat',
                        'custom_channel_name': False,
                        'id': self.channel_chat_3.id,
                        'memberCount': 2,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'guestMembers': [('insert', [])],
                    'id': self.channel_chat_3.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_chat_3.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': False,
                    'members': [
                        {
                            'active': True,
                            'display_name': 'Ernest Employee',
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'user_id': self.users[0].id,
                        },
                        {
                            'active': True,
                            'display_name': 'test2',
                            'email': 'test2@example.com',
                            'id': self.users[2].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'test2',
                            'out_of_office_date_end': False,
                            'user_id': self.users[2].id,
                        },
                    ],
                    'message_needaction_counter': 0,
                    'name': 'Ernest Employee, test2',
                    'public': 'private',
                    'rtcSessions': [('insert', [])],
                    'seen_partners_info': [
                        {
                            'fetched_message_id': False,
                            'id': self.channel_chat_3.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'partner_id': self.users[0].partner_id.id,
                            'seen_message_id': False,
                        },
                        {
                            'fetched_message_id': False,
                            'id': self.channel_chat_3.channel_member_ids.filtered(lambda m: m.partner_id == self.users[2].partner_id).id,
                            'partner_id': self.users[2].partner_id.id,
                            'seen_message_id': False,
                        },
                    ],
                    'seen_message_id': False,
                    'state': 'open',
                    'uuid': self.channel_chat_3.uuid,
                },
                {
                    'authorizedGroupFullName': False,
                    'channel': {
                        'avatarCacheKey': self.channel_chat_4._get_avatar_cache_key(),
                        'channel_type': 'chat',
                        'custom_channel_name': False,
                        'id': self.channel_chat_4.id,
                        'memberCount': 2,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'guestMembers': [('insert', [])],
                    'id': self.channel_chat_4.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_chat_4.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': False,
                    'members': [
                        {
                            'active': True,
                            'display_name': 'Ernest Employee',
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'user_id': self.users[0].id,
                        },
                        {
                            'active': True,
                            'display_name': 'test3',
                            'email': False,
                            'id': self.users[3].partner_id.id,
                            'im_status': 'offline',
                            'is_internal_user': True,
                            'name': 'test3',
                            'out_of_office_date_end': False,
                            'user_id': self.users[3].id,
                        },
                    ],
                    'message_needaction_counter': 0,
                    'name': 'Ernest Employee, test3',
                    'public': 'private',
                    'rtcSessions': [('insert', [])],
                    'seen_partners_info': [
                        {
                            'fetched_message_id': False,
                            'id': self.channel_chat_4.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'partner_id': self.users[0].partner_id.id,
                            'seen_message_id': False,
                        },
                        {
                            'fetched_message_id': False,
                            'id': self.channel_chat_4.channel_member_ids.filtered(lambda m: m.partner_id == self.users[3].partner_id).id,
                            'partner_id': self.users[3].partner_id.id,
                            'seen_message_id': False,
                        },
                    ],
                    'seen_message_id': False,
                    'state': 'open',
                    'uuid': self.channel_chat_4.uuid,
                },
                {
                    'authorizedGroupFullName': False,
                    'channel': {
                        'avatarCacheKey': self.channel_livechat_1._get_avatar_cache_key(),
                        'channel_type': 'livechat',
                        'custom_channel_name': False,
                        'id': self.channel_livechat_1.id,
                        'memberCount': 2,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'guestMembers': [('insert', [])],
                    'id': self.channel_livechat_1.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_livechat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': next(res['message_id'] for res in self.channel_livechat_1._channel_last_message_ids()),
                    'livechat_visitor': {
                        'country': False,
                        'id': self.users[1].partner_id.id,
                        'name': 'test1',
                    },
                    'members': [
                        {
                            'active': True,
                            'email': False,
                            'id': self.users[0].partner_id.id,
                            'im_status': False,
                            'livechat_username': False,
                            'name': 'Ernest Employee',
                        },
                        {
                            'active': True,
                            'email': False,
                            'id': self.users[1].partner_id.id,
                            'im_status': False,
                            'livechat_username': False,
                            'name': 'test1',
                        },
                    ],
                    'message_needaction_counter': 0,
                    'name': 'test1 Ernest Employee',
                    'operator_pid': (self.users[0].partner_id.id, 'Ernest Employee'),
                    'public': 'private',
                    'rtcSessions': [('insert', [])],
                    'seen_partners_info': [
                        {
                            'fetched_message_id': False,
                            'id': self.channel_livechat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'partner_id': self.users[0].partner_id.id,
                            'seen_message_id': False,
                        },
                        {
                            'fetched_message_id': next(res['message_id'] for res in self.channel_livechat_1._channel_last_message_ids()),
                            'id': self.channel_livechat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[1].partner_id).id,
                            'partner_id': self.users[1].partner_id.id,
                            'seen_message_id': next(res['message_id'] for res in self.channel_livechat_1._channel_last_message_ids()),
                        },
                    ],
                    'seen_message_id': False,
                    'state': 'open',
                    'uuid': self.channel_livechat_1.uuid,
                },
                {
                    'authorizedGroupFullName': False,
                    'channel': {
                        'avatarCacheKey': self.channel_livechat_2._get_avatar_cache_key(),
                        'channel_type': 'livechat',
                        'custom_channel_name': False,
                        'id': self.channel_livechat_2.id,
                        'memberCount': 2,
                        'serverMessageUnreadCounter': 0,
                    },
                    'create_uid': self.env.ref('base.public_user').id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'guestMembers': [('insert', [])],
                    'id': self.channel_livechat_2.id,
                    'invitedMembers': [('insert', [])],
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'last_message_id': next(res['message_id'] for res in self.channel_livechat_2._channel_last_message_ids()),
                    'livechat_visitor': {
                        'country': (self.env.ref('base.be').id, 'Belgium'),
                        'id': False,
                        'name': 'anon 2',
                    },
                    'members': [
                        {
                            'active': False,
                            'email': False,
                            'id': self.env.ref('base.public_partner').id,
                            'im_status': False,
                            'livechat_username': False,
                            'name': 'Public user',
                        },
                        {
                            'active': True,
                            'email': False,
                            'id': self.users[0].partner_id.id,
                            'im_status': False,
                            'livechat_username': False,
                            'name': 'Ernest Employee',
                        },
                    ],
                    'message_needaction_counter': 0,
                    'name': 'anon 2 Ernest Employee',
                    'operator_pid': (self.users[0].partner_id.id, 'Ernest Employee'),
                    'public': 'private',
                    'rtcSessions': [('insert', [])],
                    'seen_partners_info': [
                        {
                            'fetched_message_id': next(res['message_id'] for res in self.channel_livechat_2._channel_last_message_ids()),
                            'id': self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.env.ref('base.public_partner')).id,
                            'partner_id': self.env.ref('base.public_user').partner_id.id,
                            'seen_message_id': next(res['message_id'] for res in self.channel_livechat_2._channel_last_message_ids()),
                        },
                        {
                            'fetched_message_id': False,
                            'id': self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'partner_id': self.users[0].partner_id.id,
                            'seen_message_id': False,
                        },
                    ],
                    'seen_message_id': False,
                    'state': 'open',
                    'uuid': self.channel_livechat_2.uuid,
                },
            ],
            'companyName': 'YourCompany',
            'shortcodes': [
                {
                    'id': 1,
                    'source': 'hello',
                    'substitution': 'Hello. How may I help you?',
                },
                {
                    'id': 2,
                    'source': 'bye',
                    'substitution': 'Thanks for your feedback. Good bye!',
                },
            ],
            'menu_id': self.env['ir.model.data']._xmlid_to_res_id('mail.menu_root_discuss'),
            'partner_root': {
                'active': False,
                'display_name': 'OdooBot',
                'email': 'odoobot@example.com',
                'id': self.user_root.partner_id.id,
                'im_status': 'bot',
                'is_internal_user': True,
                'name': 'OdooBot',
                'out_of_office_date_end': False,
                'user_id': False,
            },
            'publicPartners': [('insert', [{
                'id': self.env.ref('base.public_partner').id,
            }])],
            'currentGuest': False,
            'current_partner': {
                'active': True,
                'display_name': 'Ernest Employee',
                'email': 'e.e@example.com',
                'id': self.users[0].partner_id.id,
                'im_status': 'offline',
                'is_internal_user': True,
                'name': 'Ernest Employee',
                'out_of_office_date_end': False,
                'user_id': self.users[0].id,
            },
            'current_user_id': self.users[0].id,
            'current_user_settings': {
                'id': self.env['res.users.settings']._find_or_create_for_user(self.users[0]).id,
                'is_discuss_sidebar_category_channel_open': True,
                'is_discuss_sidebar_category_chat_open': True,
                'is_discuss_sidebar_category_livechat_open': True,
                'push_to_talk_key': False,
                'use_push_to_talk': False,
                'user_id': {'id': self.users[0].id},
                'voice_active_duration': 0,
                'volume_settings_ids': [('insert', [])],
            },
        }

    def _get_query_count(self):
        """
            Returns the expected query count.
            The point of having a separate getter is to allow it to be overriden.
        """
        return 85
