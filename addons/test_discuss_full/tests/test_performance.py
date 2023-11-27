# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from unittest.mock import patch, PropertyMock

from odoo import Command, fields
from odoo.tests.common import users, tagged, HttpCase, warmup
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


@tagged('post_install', '-at_install')
class TestDiscussFullPerformance(HttpCase):
    _query_count = 62

    def setUp(self):
        super().setUp()
        self.group_user = self.env.ref('base.group_user')
        self.password = 'Pl1bhD@2!kXZ'
        self.env['mail.shortcode'].search([]).unlink()
        self.shortcodes = self.env['mail.shortcode'].create([
            {'source': 'hello', 'substitution': 'Hello, how may I help you?'},
            {'source': 'bye', 'substitution': 'Thanks for your feedback. Goodbye!'},
        ])
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
            {'name': 'test1', 'login': 'test1', 'password': self.password, 'email': 'test1@example.com', 'country_id': self.env.ref('base.in').id},
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
            'request_date_from': date.today() + relativedelta(days=-2),
            'request_date_to': date.today() + relativedelta(days=2),
            'employee_id': employee.id,
            'holiday_status_id': self.leave_type.id,
        } for employee in self.employees])

    @users('emp')
    @warmup
    def test_init_messaging(self):
        """Test performance of `_init_messaging`."""
        self.channel_general = self.env.ref('mail.channel_all_employees')  # Unfortunately #general cannot be deleted. Assertions below assume data from a fresh db with demo.
        self.channel_general.message_ids.unlink() # Remove messages to avoid depending on demo data.
        self.env['discuss.channel'].sudo().search([('id', '!=', self.channel_general.id)]).unlink()
        self.user_root = self.env.ref('base.user_root')
        # create public channels
        self.channel_channel_public_1 = self.env['discuss.channel'].channel_create(name='public channel 1', group_id=None)
        self.channel_channel_public_1.add_members((self.users[0] + self.users[2] + self.users[3] + self.users[4] + self.users[8]).partner_id.ids)
        self.channel_channel_public_2 = self.env['discuss.channel'].channel_create(name='public channel 2', group_id=None)
        self.channel_channel_public_2.add_members((self.users[0] + self.users[2] + self.users[4] + self.users[7] + self.users[9]).partner_id.ids)
        # create group-restricted channels
        self.channel_channel_group_1 = self.env['discuss.channel'].channel_create(name='group restricted channel 1', group_id=self.env.ref('base.group_user').id)
        self.channel_channel_group_1.add_members((self.users[0] + self.users[2] + self.users[3] + self.users[6] + self.users[12]).partner_id.ids)
        self.channel_channel_group_2 = self.env['discuss.channel'].channel_create(name='group restricted channel 2', group_id=self.env.ref('base.group_user').id)
        self.channel_channel_group_2.add_members((self.users[0] + self.users[2] + self.users[6] + self.users[7] + self.users[13]).partner_id.ids)
        # create chats
        self.channel_chat_1 = self.env['discuss.channel'].channel_get((self.users[0] + self.users[14]).partner_id.ids)
        self.channel_chat_2 = self.env['discuss.channel'].channel_get((self.users[0] + self.users[15]).partner_id.ids)
        self.channel_chat_3 = self.env['discuss.channel'].channel_get((self.users[0] + self.users[2]).partner_id.ids)
        self.channel_chat_4 = self.env['discuss.channel'].channel_get((self.users[0] + self.users[3]).partner_id.ids)
        # create groups
        self.channel_group_1 = self.env['discuss.channel'].create_group((self.users[0] + self.users[12]).partner_id.ids)
        # create livechats
        im_livechat_channel = self.env['im_livechat.channel'].sudo().create({'name': 'support', 'user_ids': [Command.link(self.users[0].id)]})
        self.env['bus.presence'].create({'user_id': self.users[0].id, 'status': 'online'})  # make available for livechat (ignore leave)
        self.authenticate('test1', self.password)
        self.channel_livechat_1 = self.env['discuss.channel'].browse(self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'anon 1',
            'channel_id': im_livechat_channel.id,
            'previous_operator_id': self.users[0].partner_id.id,
        })['id'])
        self.channel_livechat_1.with_user(self.users[1]).message_post(body="test")
        self.authenticate(None, None)
        with patch("odoo.http.GeoIP.country_code", new_callable=PropertyMock(return_value=self.env.ref('base.be').code)):
            self.channel_livechat_2 = self.env['discuss.channel'].browse(self.make_jsonrpc_request("/im_livechat/get_session", {
                'anonymous_name': 'anon 2',
                'channel_id': im_livechat_channel.id,
                'previous_operator_id': self.users[0].partner_id.id,
            })['id'])
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
        with self.assertQueryCount(emp=self._query_count):
            init_messaging = self.users[0].with_user(self.users[0])._init_messaging()

        self.assertEqual(init_messaging, self._get_init_messaging_result())

    def _get_init_messaging_result(self):
        """
            Returns the result of a call to init_messaging.

            The point of having a separate getter is to allow it to be overriden.
        """
        return {
            'initBusId': self.env['bus.bus'].sudo()._bus_last_id(),
            'hasGifPickerFeature': False,
            'hasLinkPreviewFeature': True,
            'hasMessageTranslationFeature': False,
            'needaction_inbox_counter': 1,
            'starred_counter': 1,
            'odoobotOnboarding': False,
            'channels': [
                {
                    'allow_public_upload': False,
                    'authorizedGroupFullName': self.group_user.full_name,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_general._get_avatar_cache_key(),
                    'channel_type': 'channel',
                    'channelMembers': [('ADD', sorted([{
                        'thread': {
                            'id': self.channel_general.id,
                            'model': "discuss.channel",
                        },
                        'id': self.channel_general.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                        'persona': {
                            'active': True,
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': self.users[0].partner_id.im_status,
                            'is_company': False,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'type': "partner",
                            'user': {
                                'id': self.users[0].id,
                                'isInternalUser': True,
                            },
                            'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                        },
                    }], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_general.id,
                    'memberCount': len(self.group_user.users),
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.user_root.id,
                    'defaultDisplayMode': False,
                    'description': 'General announcements for all employees.',
                    'group_based_subscription': True,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': False,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_general.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'general',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
                    'seen_message_id': False,
                    'state': 'open',
                    'uuid': self.channel_general.uuid,
                },
                {
                    'allow_public_upload': False,
                    'authorizedGroupFullName': False,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_channel_public_1._get_avatar_cache_key(),
                    'channel_type': 'channel',
                    'channelMembers': [('ADD', sorted([{
                        'thread': {
                            'id': self.channel_channel_public_1.id,
                            'model': "discuss.channel",
                        },
                        'id': self.channel_channel_public_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                        'persona': {
                            'active': True,
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': self.users[0].partner_id.im_status,
                            'is_company': False,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'type': "partner",
                            'user': {
                                'id': self.users[0].id,
                                'isInternalUser': True,
                            },
                            'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                        },
                    }], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_channel_public_1.id,
                    'memberCount': 5,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': True,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_public_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 1,
                    'name': 'public channel 1',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_public_1._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_public_1.uuid,
                },
                {
                    'allow_public_upload': False,
                    'authorizedGroupFullName': False,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_channel_public_2._get_avatar_cache_key(),
                    'channel_type': 'channel',
                    'channelMembers': [('ADD', sorted([{
                        'thread': {
                            'id': self.channel_channel_public_2.id,
                            'model': "discuss.channel",
                        },
                        'id': self.channel_channel_public_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                        'persona': {
                            'active': True,
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': self.users[0].partner_id.im_status,
                            'is_company': False,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'type': "partner",
                            'user': {
                                'id': self.users[0].id,
                                'isInternalUser': True,
                            },
                            'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                        },
                    }], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_channel_public_2.id,
                    'memberCount': 5,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': True,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_public_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'public channel 2',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_public_2._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_public_2.uuid,
                },
                {
                    'allow_public_upload': False,
                    'authorizedGroupFullName': self.group_user.full_name,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_channel_group_1._get_avatar_cache_key(),
                    'channel_type': 'channel',
                    'channelMembers': [('ADD', sorted([{
                        'thread': {
                            'id': self.channel_channel_group_1.id,
                            'model': "discuss.channel",
                        },
                        'id': self.channel_channel_group_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                        'persona': {
                            'active': True,
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': self.users[0].partner_id.im_status,
                            'is_company': False,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'type': "partner",
                            'user': {
                                'id': self.users[0].id,
                                'isInternalUser': True,
                            },
                            'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                        },
                    }], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_channel_group_1.id,
                    'memberCount': 5,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': True,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_group_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'group restricted channel 1',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_group_1._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_group_1.uuid,
                },
                {
                    'allow_public_upload': False,
                    'authorizedGroupFullName': self.group_user.full_name,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_channel_group_2._get_avatar_cache_key(),
                    'channel_type': 'channel',
                    'channelMembers': [('ADD', sorted([{
                        'thread': {
                            'id': self.channel_channel_group_2.id,
                            'model': "discuss.channel",
                        },
                        'id': self.channel_channel_group_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                        'persona': {
                            'active': True,
                            'email': 'e.e@example.com',
                            'id': self.users[0].partner_id.id,
                            'im_status': self.users[0].partner_id.im_status,
                            'is_company': False,
                            'name': 'Ernest Employee',
                            'out_of_office_date_end': False,
                            'type': "partner",
                            'user': {
                                'id': self.users[0].id,
                                'isInternalUser': True,
                            },
                            'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                        },
                    }], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_channel_group_2.id,
                    'memberCount': 5,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': True,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_channel_group_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'group restricted channel 2',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
                    'seen_message_id': next(res['message_id'] for res in self.channel_channel_group_2._channel_last_message_ids()),
                    'state': 'open',
                    'uuid': self.channel_channel_group_2.uuid,
                },
                {
                    'allow_public_upload': False,
                    'authorizedGroupFullName': False,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_group_1._get_avatar_cache_key(),
                    'channel_type': 'group',
                    'channelMembers': [('ADD', sorted([
                        {
                            'thread': {
                                'id': self.channel_group_1.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_group_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': 'e.e@example.com',
                                'id': self.users[0].partner_id.id,
                                'im_status': self.users[0].partner_id.im_status,
                                'is_company': False,
                                'name': 'Ernest Employee',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[0].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                            },
                        },
                        {
                            'thread': {
                                'id': self.channel_group_1.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_group_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[12].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': False,
                                'id': self.users[12].partner_id.id,
                                'im_status': self.users[12].partner_id.im_status,
                                'is_company': False,
                                'name': 'test12',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[12].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                            },
                        },
                    ], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_group_1.id,
                    'memberCount': 2,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': True,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_group_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': '',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
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
                    'allow_public_upload': False,
                    'authorizedGroupFullName': False,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_chat_1._get_avatar_cache_key(),
                    'channel_type': 'chat',
                    'channelMembers': [('ADD', sorted([
                        {
                            'thread': {
                                'id': self.channel_chat_1.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_chat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': 'e.e@example.com',
                                'id': self.users[0].partner_id.id,
                                'im_status': self.users[0].partner_id.im_status,
                                'is_company': False,
                                'name': 'Ernest Employee',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[0].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                            },
                        },
                        {
                            'thread': {
                                'id': self.channel_chat_1.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_chat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[14].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': False,
                                'id': self.users[14].partner_id.id,
                                'im_status': self.users[14].partner_id.im_status,
                                'is_company': False,
                                'name': 'test14',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[14].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                            },
                        },
                    ], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_chat_1.id,
                    'memberCount': 2,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': False,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_chat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'Ernest Employee, test14',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
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
                    'allow_public_upload': False,
                    'authorizedGroupFullName': False,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_chat_2._get_avatar_cache_key(),
                    'channel_type': 'chat',
                    'channelMembers': [('ADD', sorted([
                        {
                            'thread': {
                                'id': self.channel_chat_2.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_chat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': 'e.e@example.com',
                                'id': self.users[0].partner_id.id,
                                'im_status': self.users[0].partner_id.im_status,
                                'is_company': False,
                                'name': 'Ernest Employee',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[0].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                            },
                        },
                        {
                            'thread': {
                                'id': self.channel_chat_2.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_chat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[15].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': False,
                                'id': self.users[15].partner_id.id,
                                'im_status': self.users[15].partner_id.im_status,
                                'is_company': False,
                                'name': 'test15',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[15].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                            },
                        },
                    ], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_chat_2.id,
                    'memberCount': 2,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': False,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_chat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'Ernest Employee, test15',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
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
                    'allow_public_upload': False,
                    'authorizedGroupFullName': False,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_chat_3._get_avatar_cache_key(),
                    'channel_type': 'chat',
                    'channelMembers': [('ADD', sorted([
                        {
                            'thread': {
                                'id': self.channel_chat_3.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_chat_3.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': 'e.e@example.com',
                                'id': self.users[0].partner_id.id,
                                'im_status': self.users[0].partner_id.im_status,
                                'is_company': False,
                                'name': 'Ernest Employee',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[0].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                            },
                        },
                        {
                            'thread': {
                                'id': self.channel_chat_3.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_chat_3.channel_member_ids.filtered(lambda m: m.partner_id == self.users[2].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': 'test2@example.com',
                                'id': self.users[2].partner_id.id,
                                'im_status': self.users[2].partner_id.im_status,
                                'is_company': False,
                                'name': 'test2',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[2].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                            },
                        },
                    ], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_chat_3.id,
                    'memberCount': 2,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': False,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_chat_3.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'Ernest Employee, test2',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
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
                    'allow_public_upload': False,
                    'authorizedGroupFullName': False,
                    'anonymous_country': False,
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_chat_4._get_avatar_cache_key(),
                    'channel_type': 'chat',
                    'channelMembers': [('ADD', sorted([
                        {
                            'thread': {
                                'id': self.channel_chat_4.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_chat_4.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': 'e.e@example.com',
                                'id': self.users[0].partner_id.id,
                                'im_status': self.users[0].partner_id.im_status,
                                'is_company': False,
                                'name': 'Ernest Employee',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[0].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
                            },
                        },
                        {
                            'thread': {
                                'id': self.channel_chat_4.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_chat_4.channel_member_ids.filtered(lambda m: m.partner_id == self.users[3].partner_id).id,
                            'persona': {
                                'active': True,
                                'email': False,
                                'id': self.users[3].partner_id.id,
                                'im_status': self.users[3].partner_id.im_status,
                                'is_company': False,
                                'name': 'test3',
                                'out_of_office_date_end': False,
                                'type': "partner",
                                'user': {
                                    'id': self.users[3].id,
                                    'isInternalUser': True,
                                },
                                'write_date': fields.Datetime.to_string(self.users[3].partner_id.write_date),
                            },
                        },
                    ], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_chat_4.id,
                    'memberCount': 2,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.user.id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': False,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_chat_4.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'Ernest Employee, test3',
                    'rtcSessions': [('ADD', [])],
                    "custom_notifications": False,
                    'mute_until_dt': False,
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
                    'allow_public_upload': False,
                    'authorizedGroupFullName': False,
                    'anonymous_country': {
                        'code': 'IN',
                        'id': self.env.ref('base.in').id,
                        'name': 'India',
                    },
                    'anonymous_name': False,
                    'avatarCacheKey': self.channel_livechat_1._get_avatar_cache_key(),
                    'channel_type': 'livechat',
                    'channelMembers': [('ADD', sorted([
                        {
                            'thread': {
                                'id': self.channel_livechat_1.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_livechat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'persona': {
                                'active': True,
                                'country': False,
                                'id': self.users[0].partner_id.id,
                                'is_bot': False,
                                'is_public': False,
                                'name': 'Ernest Employee',
                                'type': "partner",
                            },
                        },
                        {
                            'thread': {
                                'id': self.channel_livechat_1.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_livechat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[1].partner_id).id,
                            'persona': {
                                'active': True,
                                'country': {
                                    'code': 'IN',
                                    'id': self.env.ref('base.in').id,
                                    'name': 'India',
                                },
                                'id': self.users[1].partner_id.id,
                                'is_bot': False,
                                'is_public': False,
                                'name': 'test1',
                                'type': "partner",
                            },
                        },
                    ], key=lambda member_data: member_data['id']))],
                    'custom_channel_name': False,
                    'id': self.channel_livechat_1.id,
                    'memberCount': 2,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.users[1].id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': False,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_livechat_1.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'test1 Ernest Employee',
                    "custom_notifications": False,
                    'mute_until_dt': False,
                    'operator_pid': (self.users[0].partner_id.id, 'Ernest Employee'),
                    'rtcSessions': [('ADD', [])],
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
                    'allow_public_upload': False,
                    'authorizedGroupFullName': False,
                    'anonymous_country': {
                        'id': self.env.ref('base.be').id,
                        'code': 'BE',
                        'name': 'Belgium',
                    },
                    'anonymous_name': 'anon 2',
                    'avatarCacheKey': self.channel_livechat_2._get_avatar_cache_key(),
                    'channel_type': 'livechat',
                    'channelMembers': [('ADD', [
                        {
                            'thread': {
                                'id': self.channel_livechat_2.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).id,
                            'persona': {
                                'active': True,
                                'country': False,
                                'id': self.users[0].partner_id.id,
                                'is_bot': False,
                                'is_public': False,
                                'name': 'Ernest Employee',
                                'type': "partner",
                            },
                        },
                        {
                            'thread': {
                                'id': self.channel_livechat_2.id,
                                'model': "discuss.channel",
                            },
                            'id': self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.guest_id).id,
                            'persona': {
                                'id': self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.guest_id).guest_id.id,
                                'im_status': self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.guest_id).guest_id.im_status,
                                'name': self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.guest_id).guest_id.name,
                                'type': "guest",
                                'write_date': fields.Datetime.to_string(self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.guest_id).guest_id.write_date),
                            },
                        },
                    ])],
                    'custom_channel_name': False,
                    'id': self.channel_livechat_2.id,
                    'memberCount': 2,
                    'message_unread_counter': 0,
                    'model': "discuss.channel",
                    'create_uid': self.env.ref('base.public_user').id,
                    'defaultDisplayMode': False,
                    'description': False,
                    'group_based_subscription': False,
                    'invitedMembers': [('ADD', [])],
                    'is_editable': False,
                    'is_minimized': False,
                    'is_pinned': True,
                    'last_interest_dt': self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.partner_id == self.users[0].partner_id).last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'message_needaction_counter': 0,
                    'name': 'anon 2 Ernest Employee',
                    "custom_notifications": False,
                    'mute_until_dt': False,
                    'operator_pid': (self.users[0].partner_id.id, 'Ernest Employee'),
                    'rtcSessions': [('ADD', [])],
                    'seen_partners_info': [
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
                    'id': self.shortcodes[0].id,
                    'source': 'hello',
                    'substitution': 'Hello, how may I help you?',
                },
                {
                    'id': self.shortcodes[1].id,
                    'source': 'bye',
                    'substitution': 'Thanks for your feedback. Goodbye!',
                },
            ],
            'internalUserGroupId': self.env.ref('base.group_user').id,
            'menu_id': self.env['ir.model.data']._xmlid_to_res_id('mail.menu_root_discuss'),
            'mt_comment_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            'odoobot': {
                'active': False,
                'email': 'odoobot@example.com',
                'id': self.user_root.partner_id.id,
                'im_status': 'bot',
                'is_company': False,
                'name': 'OdooBot',
                'out_of_office_date_end': False,
                'type': "partner",
                'user': False,
                'write_date': fields.Datetime.to_string(self.user_root.partner_id.write_date),
            },
            'currentGuest': False,
            'current_partner': {
                'active': True,
                'email': 'e.e@example.com',
                'id': self.users[0].partner_id.id,
                'im_status': self.users[0].partner_id.im_status,
                'is_company': False,
                'name': 'Ernest Employee',
                'out_of_office_date_end': False,
                'type': "partner",
                'user': {
                    'id': self.users[0].id,
                    'isInternalUser': True,
                },
                'write_date': fields.Datetime.to_string(self.users[0].partner_id.write_date),
            },
            'current_user_id': self.users[0].id,
            'current_user_settings': {
                'id': self.env['res.users.settings']._find_or_create_for_user(self.users[0]).id,
                'is_discuss_sidebar_category_channel_open': True,
                'is_discuss_sidebar_category_chat_open': True,
                'is_discuss_sidebar_category_livechat_open': True,
                'push_to_talk_key': False,
                'use_push_to_talk': False,
                'livechat_lang_ids': [],
                'livechat_username': False,
                'user_id': {'id': self.users[0].id},
                'voice_active_duration': 0,
                'volume_settings_ids': [('ADD', [])],
            },
        }
