# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from unittest.mock import patch, PropertyMock

from odoo import Command, fields
from odoo.tests.common import users, tagged, HttpCase, warmup


@tagged('post_install', '-at_install')
class TestDiscussFullPerformance(HttpCase):
    _query_count = 66
    _query_count_discuss_channels = 69

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
                'password': self.password,
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
            'request_date_from': fields.Datetime.today() + relativedelta(days=-2),
            'request_date_to': fields.Datetime.today() + relativedelta(days=2),
            'employee_id': employee.id,
            'holiday_status_id': self.leave_type.id,
        } for employee in self.employees])

    def _setup_test(self):
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
        guest_sudo = self.channel_livechat_2.channel_member_ids.filtered(lambda m: m.guest_id).guest_id.sudo()
        self.make_jsonrpc_request("/mail/message/post", {
            "post_data": {
                "body": "test",
                "message_type": "comment",
            },
            "thread_id": self.channel_livechat_2.id,
            "thread_model": "discuss.channel",
        }, headers={"Cookie": f"{guest_sudo._cookie_name}={guest_sudo._format_auth_cookie()};"})
        # add needaction
        self.users[0].notification_type = 'inbox'
        message = self.channel_channel_public_1.message_post(body='test', message_type='comment', author_id=self.users[2].partner_id.id, partner_ids=self.users[0].partner_id.ids)
        # add star
        message.toggle_message_starred()
        self.env.company.sudo().name = 'YourCompany'
        # add folded channel
        members = self.channel_chat_1.channel_member_ids
        member = members.with_user(self.users[0]).filtered(lambda m: m.is_self)
        member.fold_state = "open"
        # add call invitation
        members = self.channel_channel_group_1.channel_member_ids
        member_0 = members.with_user(self.users[0]).filtered(lambda m: m.is_self)
        member_2 = members.with_user(self.users[2]).filtered(lambda m: m.is_self)
        self.channel_channel_group_1_invited_member = member_0
        self.channel_channel_group_1_inviting_member = member_2
        # sudo: discuss.channel.rtc.session - creating a session in a test file
        data = {"channel_id": self.channel_channel_group_1.id, "channel_member_id": member_2.id}
        session = self.env["discuss.channel.rtc.session"].sudo().create(data)
        member_0.rtc_inviting_session_id = session
        self.channel_channel_group_1_inviting_session = session

    @users('emp')
    @warmup
    def test_init_messaging(self):
        """Test performance of `_init_messaging`."""
        self._setup_test()
        self.maxDiff = None
        self.env.flush_all()
        self.env.invalidate_all()
        self.authenticate(self.users[0].login, self.password)
        with self.assertQueryCount(emp=self._query_count):
            init_messaging = self.make_jsonrpc_request("/mail/init_messaging")
        self.assertEqual(init_messaging, self._get_init_messaging_result())

    def _get_init_messaging_result(self):
        """Returns the result of a call to init_messaging.
        The point of having a separate getter is to allow it to be overriden.
        """
        return {
            "CannedResponse": [
                {
                    "id": self.shortcodes[0].id,
                    "source": "hello",
                    "substitution": "Hello, how may I help you?",
                },
                {
                    "id": self.shortcodes[1].id,
                    "source": "bye",
                    "substitution": "Thanks for your feedback. Goodbye!",
                },
            ],
            "Store": {
                "action_discuss_id": self.env["ir.model.data"]._xmlid_to_res_id("mail.action_discuss"),
                "companyName": "YourCompany",
                "current_user_id": self.users[0].id,
                "discuss": {
                    "inbox": {"counter": 1, "id": "inbox", "model": "mail.box"},
                    "starred": {"counter": 1, "id": "starred", "model": "mail.box"},
                },
                "hasGifPickerFeature": False,
                "hasLinkPreviewFeature": True,
                "hasMessageTranslationFeature": False,
                "initBusId": self.env["bus.bus"].sudo()._bus_last_id(),
                "initChannelsUnreadCounter": 1,
                "internalUserGroupId": self.env.ref("base.group_user").id,
                "mt_comment_id": self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment"),
                "odoobot": {
                    "active": False,
                    "email": "odoobot@example.com",
                    "id": self.user_root.partner_id.id,
                    "im_status": "bot",
                    "is_company": False,
                    "name": "OdooBot",
                    "notification_preference": False,
                    "out_of_office_date_end": False,
                    "type": "partner",
                    "user": False,
                    "write_date": fields.Datetime.to_string(self.user_root.partner_id.write_date),
                },
                "odoobotOnboarding": False,
                "self": {
                    "active": True,
                    "email": "e.e@example.com",
                    "id": self.users[0].partner_id.id,
                    "im_status": "online",
                    "is_company": False,
                    "name": "Ernest Employee",
                    "notification_preference": "inbox",
                    "out_of_office_date_end": False,
                    "type": "partner",
                    "user": {
                        "id": self.users[0].id,
                        "isInternalUser": True,
                    },
                    "write_date": fields.Datetime.to_string(self.users[0].partner_id.write_date),
                },
                "settings": {
                    "id": self.env["res.users.settings"]._find_or_create_for_user(self.users[0]).id,
                    "is_discuss_sidebar_category_channel_open": True,
                    "is_discuss_sidebar_category_chat_open": True,
                    "is_discuss_sidebar_category_livechat_open": True,
                    "livechat_lang_ids": [],
                    "livechat_username": False,
                    "push_to_talk_key": False,
                    "use_push_to_talk": False,
                    "user_id": {"id": self.users[0].id},
                    "voice_active_duration": 0,
                    "volumes": [["ADD", []]],
                },
            },
            "Thread": [
                self._expected_result_for_channel(self.channel_channel_group_1),
                self._expected_result_for_channel(self.channel_chat_1),
            ],
        }

    @users("emp")
    @warmup
    def test_discuss_channels(self):
        """Test performance of `/discuss/channels`."""
        self._setup_test()
        self.maxDiff = None
        self.env.flush_all()
        self.env.invalidate_all()
        self.authenticate(self.users[0].login, self.password)
        with self.assertQueryCount(emp=self._query_count_discuss_channels):
            discuss_channels = self.make_jsonrpc_request("/discuss/channels")
        self.assertEqual(discuss_channels, self._get_discuss_channels_result())

    def _get_discuss_channels_result(self):
        """Returns the result of a call to discuss/channels.
        The point of having a separate getter is to allow it to be overriden.
        """
        return {
            "Message": [
                self._expected_result_for_message(self.channel_channel_public_1),
                self._expected_result_for_message(self.channel_channel_public_2),
                self._expected_result_for_message(self.channel_channel_group_1),
                self._expected_result_for_message(self.channel_channel_group_2),
                self._expected_result_for_message(self.channel_livechat_1),
                self._expected_result_for_message(self.channel_livechat_2),
            ],
            "Thread": [
                self._expected_result_for_channel(self.channel_general),
                self._expected_result_for_channel(self.channel_channel_public_1),
                self._expected_result_for_channel(self.channel_channel_public_2),
                self._expected_result_for_channel(self.channel_channel_group_1),
                self._expected_result_for_channel(self.channel_channel_group_2),
                self._expected_result_for_channel(self.channel_group_1),
                self._expected_result_for_channel(self.channel_chat_1),
                self._expected_result_for_channel(self.channel_chat_2),
                self._expected_result_for_channel(self.channel_chat_3),
                self._expected_result_for_channel(self.channel_chat_4),
                self._expected_result_for_channel(self.channel_livechat_1),
                self._expected_result_for_channel(self.channel_livechat_2),
            ],
        }

    def _expected_result_for_channel(self, channel):
        members = channel.channel_member_ids
        member_0 = members.filtered(lambda m: m.partner_id == self.users[0].partner_id)
        last_interest_dt = fields.Datetime.to_string(member_0.last_interest_dt)
        write_date_0 = fields.Datetime.to_string(self.users[0].partner_id.write_date)
        member_1 = members.filtered(lambda m: m.partner_id == self.users[1].partner_id)
        member_2 = members.filtered(lambda m: m.partner_id == self.users[2].partner_id)
        member_3 = members.filtered(lambda m: m.partner_id == self.users[3].partner_id)
        member_12 = members.filtered(lambda m: m.partner_id == self.users[12].partner_id)
        member_14 = members.filtered(lambda m: m.partner_id == self.users[14].partner_id)
        member_15 = members.filtered(lambda m: m.partner_id == self.users[15].partner_id)
        member_g = members.filtered(lambda m: m.guest_id)
        guest = member_g.guest_id
        last_message = channel._get_last_messages()
        if channel == self.channel_general:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": self.group_user.full_name,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "channel",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                }
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": len(self.group_user.users),
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.user_root.id,
                "defaultDisplayMode": False,
                "description": "General announcements for all employees.",
                "group_based_subscription": True,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "general",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_channel_public_1:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "channel",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": {"id": last_message.id},
                                    "seen_message_id": {"id": last_message.id},
                                }
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 5,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": True,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 1,
                "name": "public channel 1",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": last_message.id,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_channel_public_2:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "channel",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": {"id": last_message.id},
                                    "seen_message_id": {"id": last_message.id},
                                }
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 5,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": True,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "public channel 2",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": last_message.id,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_channel_group_1:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": self.group_user.full_name,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "channel",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": {"id": last_message.id},
                                    "seen_message_id": {"id": last_message.id},
                                }
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 5,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [
                    [
                        "ADD",
                        [
                            {
                                "id": self.channel_channel_group_1_invited_member.id,
                                "persona": {
                                    "id": self.channel_channel_group_1_invited_member.partner_id.id,
                                    "im_status": "online",
                                    "name": "Ernest Employee",
                                    "type": "partner",
                                },
                                "thread": {
                                    "id": channel.id,
                                    "model": "discuss.channel",
                                },
                            },
                        ],
                    ],
                ],
                "is_editable": True,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "group restricted channel 1",
                "rtcInvitingSession": {
                    "id": self.channel_channel_group_1_inviting_session.id,
                    "channelMember": {
                        "id": self.channel_channel_group_1_inviting_member.id,
                        "persona": {
                            "id": self.channel_channel_group_1_inviting_member.partner_id.id,
                            "im_status": "offline",
                            "name": "test2",
                            "type": "partner",
                        },
                        "thread": {
                            "id": channel.id,
                            "model": "discuss.channel",
                        },
                    },
                },
                "rtcSessions": [
                    [
                        "ADD",
                        [
                            {
                                "channelMember": {
                                    "id": self.channel_channel_group_1_inviting_member.id,
                                    "persona": {
                                        "id": self.channel_channel_group_1_inviting_member.partner_id.id,
                                        "im_status": "offline",
                                        "name": "test2",
                                        "type": "partner",
                                    },
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                },
                                "id": self.channel_channel_group_1_inviting_session.id,
                                "isCameraOn": False,
                                "isDeaf": False,
                                "isScreenSharingOn": False,
                                "isSelfMuted": False,
                            }
                        ],
                    ]
                ],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": last_message.id,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_channel_group_2:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": self.group_user.full_name,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "channel",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": {"id": last_message.id},
                                    "seen_message_id": {"id": last_message.id},
                                }
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 5,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": True,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "group restricted channel 2",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": last_message.id,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_group_1:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "group",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_12.id,
                                    "persona": {
                                        "active": True,
                                        "email": False,
                                        "id": self.users[12].partner_id.id,
                                        "im_status": "offline",
                                        "is_company": False,
                                        "name": "test12",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "email",
                                        "user": {
                                            "id": self.users[12].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 2,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": True,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_chat_1:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "chat",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_14.id,
                                    "persona": {
                                        "active": True,
                                        "email": False,
                                        "id": self.users[14].partner_id.id,
                                        "im_status": "offline",
                                        "is_company": False,
                                        "name": "test14",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "email",
                                        "user": {
                                            "id": self.users[14].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 2,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "Ernest Employee, test14",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": False,
                "state": "open",
                "uuid": channel.uuid,
            }
        if channel == self.channel_chat_2:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "chat",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_15.id,
                                    "persona": {
                                        "active": True,
                                        "email": False,
                                        "id": self.users[15].partner_id.id,
                                        "im_status": "offline",
                                        "is_company": False,
                                        "name": "test15",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "email",
                                        "user": {
                                            "id": self.users[15].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 2,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "Ernest Employee, test15",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_chat_3:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "chat",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_2.id,
                                    "persona": {
                                        "active": True,
                                        "email": "test2@example.com",
                                        "id": self.users[2].partner_id.id,
                                        "im_status": "offline",
                                        "is_company": False,
                                        "name": "test2",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "email",
                                        "user": {
                                            "id": self.users[2].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 2,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "Ernest Employee, test2",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_chat_4:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "chat",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "email": "e.e@example.com",
                                        "id": self.users[0].partner_id.id,
                                        "im_status": "online",
                                        "is_company": False,
                                        "name": "Ernest Employee",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "inbox",
                                        "user": {
                                            "id": self.users[0].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": write_date_0,
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_3.id,
                                    "persona": {
                                        "active": True,
                                        "email": False,
                                        "id": self.users[3].partner_id.id,
                                        "im_status": "offline",
                                        "is_company": False,
                                        "name": "test3",
                                        "out_of_office_date_end": False,
                                        "type": "partner",
                                        "notification_preference": "email",
                                        "user": {
                                            "id": self.users[3].id,
                                            "isInternalUser": True,
                                        },
                                        "write_date": fields.Datetime.to_string(
                                            self.users[3].partner_id.write_date
                                        ),
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 2,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "Ernest Employee, test3",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "seen_message_id": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_livechat_1:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": {
                    "code": "IN",
                    "id": self.env.ref("base.in").id,
                    "name": "India",
                },
                "anonymous_name": False,
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "livechat",
                "channelMembers": [
                    [
                        "ADD",
                        sorted(
                            [
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_0.id,
                                    "persona": {
                                        "active": True,
                                        "country": False,
                                        "id": self.users[0].partner_id.id,
                                        "is_bot": False,
                                        "is_public": False,
                                        "name": "Ernest Employee",
                                        "type": "partner",
                                    },
                                    "fetched_message_id": False,
                                    "seen_message_id": False,
                                },
                                {
                                    "thread": {
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                    },
                                    "id": member_1.id,
                                    "persona": {
                                        "active": True,
                                        "country": {
                                            "code": "IN",
                                            "id": self.env.ref("base.in").id,
                                            "name": "India",
                                        },
                                        "id": self.users[1].partner_id.id,
                                        "is_bot": False,
                                        "is_public": False,
                                        "name": "test1",
                                        "type": "partner",
                                    },
                                    "fetched_message_id": {"id": last_message.id},
                                    "seen_message_id": {"id": last_message.id},
                                },
                            ],
                            key=lambda member_data: member_data["id"],
                        ),
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 2,
                "message_unread_counter": 0,
                "model": "discuss.channel",
                "create_uid": self.users[1].id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "test1 Ernest Employee",
                "custom_notifications": False,
                "mute_until_dt": False,
                "operator": {
                    "id": self.users[0].partner_id.id,
                    "name": "Ernest Employee",
                    "type": "partner",
                    "write_date": write_date_0,
                },
                "rtcSessions": [["ADD", []]],
                "seen_message_id": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_livechat_2:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": {
                    "id": self.env.ref("base.be").id,
                    "code": "BE",
                    "name": "Belgium",
                },
                "anonymous_name": "anon 2",
                "avatarCacheKey": channel._get_avatar_cache_key(),
                "channel_type": "livechat",
                "channelMembers": [
                    [
                        "ADD",
                        [
                            {
                                "thread": {
                                    "id": channel.id,
                                    "model": "discuss.channel",
                                },
                                "id": member_0.id,
                                "persona": {
                                    "active": True,
                                    "country": False,
                                    "id": self.users[0].partner_id.id,
                                    "is_bot": False,
                                    "is_public": False,
                                    "name": "Ernest Employee",
                                    "type": "partner",
                                },
                                "fetched_message_id": False,
                                "seen_message_id": False,
                            },
                            {
                                "thread": {
                                    "id": channel.id,
                                    "model": "discuss.channel",
                                },
                                "id": member_g.id,
                                "persona": {
                                    "id": guest.id,
                                    "im_status": "offline",
                                    "name": "Visitor",
                                    "type": "guest",
                                    "write_date": fields.Datetime.to_string(guest.write_date),
                                },
                                "fetched_message_id": {"id": last_message.id},
                                "seen_message_id": {"id": last_message.id},
                            },
                        ],
                    ]
                ],
                "custom_channel_name": False,
                "id": channel.id,
                "memberCount": 2,
                "message_unread_counter": 1,
                "model": "discuss.channel",
                "create_uid": self.env.ref("base.public_user").id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "name": "anon 2 Ernest Employee",
                "custom_notifications": False,
                "mute_until_dt": False,
                "operator": {
                    "id": self.users[0].partner_id.id,
                    "name": "Ernest Employee",
                    "type": "partner",
                    "write_date": write_date_0,
                },
                "rtcSessions": [["ADD", []]],
                "seen_message_id": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        return {}

    def _expected_result_for_message(self, channel):
        last_message = channel._get_last_messages()
        create_date = fields.Datetime.to_string(last_message.create_date)
        date = fields.Datetime.to_string(last_message.date)
        write_date = fields.Datetime.to_string(last_message.write_date)
        user_0 = self.users[0]
        write_date_0 = fields.Datetime.to_string(user_0.partner_id.write_date)
        user_1 = self.users[1]
        write_date_1 = fields.Datetime.to_string(user_1.partner_id.write_date)
        user_2 = self.users[2]
        write_date_2 = fields.Datetime.to_string(user_2.partner_id.write_date)
        user_9 = self.users[9]
        user_12 = self.users[12]
        user_13 = self.users[13]
        members = channel.channel_member_ids
        member_g = members.filtered(lambda m: m.guest_id)
        guest = member_g.guest_id
        mt_note_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")
        mt_comment_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment")
        if channel == self.channel_channel_public_1:
            return {
                "attachments": [],
                "author": {
                    "id": user_2.partner_id.id,
                    "is_company": False,
                    "name": "test2",
                    "notification_preference": "email",
                    "type": "partner",
                    "user": {"id": user_2.id, "isInternalUser": True},
                    "write_date": write_date_2,
                },
                "body": "<p>test</p>",
                "create_date": create_date,
                "date": date,
                "default_subject": "public channel 1",
                "email_from": '"test2" <test2@example.com>',
                "history_partner_ids": [],
                "id": last_message.id,
                "is_discussion": False,
                "is_note": True,
                "linkPreviews": [],
                "message_type": "comment",
                "model": "discuss.channel",
                "needaction_partner_ids": [self.users[0].partner_id.id],
                "notifications": [
                    {
                        "failure_type": False,
                        "id": last_message.notification_ids.id,
                        "notification_status": "sent",
                        "notification_type": "inbox",
                        "persona": {
                            "displayName": "Ernest Employee",
                            "id": self.users[0].partner_id.id,
                            "type": "partner",
                        },
                    },
                ],
                "originThread": {
                    "id": channel.id,
                    "model": "discuss.channel",
                    "module_icon": "/mail/static/description/icon.png",
                },
                "pinned_at": False,
                "reactions": [],
                "recipients": [
                    {
                        "id": self.users[0].partner_id.id,
                        "name": "Ernest Employee",
                        "type": "partner",
                    },
                ],
                "record_name": "public channel 1",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "sms_ids": [],
                "starredPersonas": [{"id": self.users[0].partner_id.id, "type": "partner"}],
                "subject": False,
                "subtype_description": False,
                "subtype_id": [mt_note_id, "Note"],
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_channel_public_2:
            return {
                "attachments": [],
                "author": {
                    "id": user_0.partner_id.id,
                    "is_company": False,
                    "name": "Ernest Employee",
                    "notification_preference": "inbox",
                    "type": "partner",
                    "user": {"id": user_0.id, "isInternalUser": True},
                    "write_date": write_date_0,
                },
                "body": f'<div class="o_mail_notification">invited <a href="#" data-oe-model="res.partner" data-oe-id="{user_9.partner_id.id}">test9</a> to the channel</div>',
                "create_date": create_date,
                "date": date,
                "default_subject": "public channel 2",
                "email_from": '"Ernest Employee" <e.e@example.com>',
                "history_partner_ids": [],
                "id": last_message.id,
                "is_discussion": True,
                "is_note": False,
                "linkPreviews": [],
                "message_type": "notification",
                "model": "discuss.channel",
                "needaction_partner_ids": [],
                "notifications": [],
                "originThread": {
                    "id": channel.id,
                    "model": "discuss.channel",
                    "module_icon": "/mail/static/description/icon.png",
                },
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "public channel 2",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "sms_ids": [],
                "starredPersonas": [],
                "subject": False,
                "subtype_description": False,
                "subtype_id": [mt_comment_id, "Discussions"],
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_channel_group_1:
            return {
                "attachments": [],
                "author": {
                    "id": user_0.partner_id.id,
                    "is_company": False,
                    "name": "Ernest Employee",
                    "notification_preference": "inbox",
                    "type": "partner",
                    "user": {"id": user_0.id, "isInternalUser": True},
                    "write_date": write_date_0,
                },
                "body": f'<div class="o_mail_notification">invited <a href="#" data-oe-model="res.partner" data-oe-id="{user_12.partner_id.id}">test12</a> to the channel</div>',
                "create_date": create_date,
                "date": date,
                "default_subject": "group restricted channel 1",
                "email_from": '"Ernest Employee" <e.e@example.com>',
                "history_partner_ids": [],
                "id": last_message.id,
                "is_discussion": True,
                "is_note": False,
                "linkPreviews": [],
                "message_type": "notification",
                "model": "discuss.channel",
                "needaction_partner_ids": [],
                "notifications": [],
                "originThread": {
                    "id": channel.id,
                    "model": "discuss.channel",
                    "module_icon": "/mail/static/description/icon.png",
                },
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "group restricted channel 1",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "sms_ids": [],
                "starredPersonas": [],
                "subject": False,
                "subtype_description": False,
                "subtype_id": [mt_comment_id, "Discussions"],
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_channel_group_2:
            return {
                "attachments": [],
                "author": {
                    "id": user_0.partner_id.id,
                    "is_company": False,
                    "name": "Ernest Employee",
                    "notification_preference": "inbox",
                    "type": "partner",
                    "user": {"id": user_0.id, "isInternalUser": True},
                    "write_date": write_date_0,
                },
                "body": f'<div class="o_mail_notification">invited <a href="#" data-oe-model="res.partner" data-oe-id="{user_13.partner_id.id}">test13</a> to the channel</div>',
                "create_date": create_date,
                "date": date,
                "default_subject": "group restricted channel 2",
                "email_from": '"Ernest Employee" <e.e@example.com>',
                "history_partner_ids": [],
                "id": last_message.id,
                "is_discussion": True,
                "is_note": False,
                "linkPreviews": [],
                "message_type": "notification",
                "model": "discuss.channel",
                "needaction_partner_ids": [],
                "notifications": [],
                "originThread": {
                    "id": channel.id,
                    "model": "discuss.channel",
                    "module_icon": "/mail/static/description/icon.png",
                },
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "group restricted channel 2",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "sms_ids": [],
                "starredPersonas": [],
                "subject": False,
                "subtype_description": False,
                "subtype_id": [mt_comment_id, "Discussions"],
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_livechat_1:
            return {
                "attachments": [],
                "author": {
                    "id": user_1.partner_id.id,
                    "is_company": False,
                    "name": "test1",
                    "notification_preference": "email",
                    "type": "partner",
                    "user": {"id": user_1.id, "isInternalUser": True},
                    "write_date": write_date_1,
                },
                "body": "<p>test</p>",
                "create_date": create_date,
                "date": date,
                "default_subject": "test1 Ernest Employee",
                "history_partner_ids": [],
                "id": last_message.id,
                "is_discussion": False,
                "is_note": True,
                "linkPreviews": [],
                "message_type": "notification",
                "model": "discuss.channel",
                "needaction_partner_ids": [],
                "notifications": [],
                "originThread": {
                    "id": channel.id,
                    "model": "discuss.channel",
                    "module_icon": "/mail/static/description/icon.png",
                },
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "test1 Ernest Employee",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "sms_ids": [],
                "starredPersonas": [],
                "subject": False,
                "subtype_description": False,
                "subtype_id": [mt_note_id, "Note"],
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_livechat_2:
            return {
                "attachments": [],
                "author": {"id": guest.id, "name": "Visitor", "type": "guest"},
                "body": "<p>test</p>",
                "create_date": create_date,
                "date": date,
                "default_subject": "anon 2 Ernest Employee",
                "email_from": False,
                "history_partner_ids": [],
                "id": last_message.id,
                "is_discussion": False,
                "is_note": True,
                "linkPreviews": [],
                "message_type": "comment",
                "model": "discuss.channel",
                "needaction_partner_ids": [],
                "notifications": [],
                "originThread": {
                    "id": channel.id,
                    "model": "discuss.channel",
                    "module_icon": "/mail/static/description/icon.png",
                },
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "anon 2 Ernest Employee",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "sms_ids": [],
                "starredPersonas": [],
                "subject": False,
                "subtype_description": False,
                "subtype_id": [mt_note_id, "Note"],
                "trackingValues": [],
                "write_date": write_date,
            }
        return {}
