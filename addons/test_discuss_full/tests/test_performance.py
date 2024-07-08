# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from unittest.mock import patch, PropertyMock

from odoo import Command, fields
from odoo.addons.mail.tools.discuss import Store
from odoo.tests.common import users, tagged, HttpCase, warmup


@tagged('post_install', '-at_install')
class TestDiscussFullPerformance(HttpCase):
    # Queries for _query_count_init_store:
    #     1: action_discuss_id
    #     1: hasGifPickerFeature
    #     1: hasLinkPreviewFeature
    #     1: hasMessageTranslationFeature
    #     1: internalUserGroupId
    #     1: mt_comment_id
    #     6: odoobot format
    #     4: settings
    #     1: has_access_livechat
    _query_count_init_store = 17
    _query_count = 49 + 1  # +1 is necessary to fix nondeterministic issue on runbot
    # Queries for _query_count_discuss_channels:
    #     1: bus last id
    _query_count_discuss_channels = 69

    def setUp(self):
        super().setUp()
        self.group_user = self.env.ref('base.group_user')
        self.password = 'Pl1bhD@2!kXZ'
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
        self.channel_general.last_interest_dt = False  # Reset state
        self.channel_general.channel_member_ids.sudo().last_interest_dt = False  # Reset state
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
        self.im_livechat_channel = self.env['im_livechat.channel'].sudo().create({'name': 'support', 'user_ids': [Command.link(self.users[0].id)]})
        self.env['bus.presence'].create({'user_id': self.users[0].id, 'status': 'online'})  # make available for livechat (ignore leave)
        self.authenticate('test1', self.password)
        self.channel_livechat_1 = self.env['discuss.channel'].browse(self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'anon 1',
            'channel_id': self.im_livechat_channel.id,
            'previous_operator_id': self.users[0].partner_id.id,
        })["Thread"][0]['id'])
        self.channel_livechat_1.with_user(self.users[1]).message_post(body="test")
        self.authenticate(None, None)
        with patch("odoo.http.GeoIP.country_code", new_callable=PropertyMock(return_value=self.env.ref('base.be').code)):
            self.channel_livechat_2 = self.env['discuss.channel'].browse(self.make_jsonrpc_request("/im_livechat/get_session", {
                'anonymous_name': 'anon 2',
                'channel_id': self.im_livechat_channel.id,
                'previous_operator_id': self.users[0].partner_id.id,
            })["Thread"][0]['id'])
        self.guest = self.channel_livechat_2.channel_member_ids.guest_id.sudo()
        self.make_jsonrpc_request("/mail/message/post", {
            "post_data": {
                "body": "test",
                "message_type": "comment",
            },
            "thread_id": self.channel_livechat_2.id,
            "thread_model": "discuss.channel",
        }, headers={"Cookie": f"{self.guest._cookie_name}={self.guest._format_auth_cookie()};"})
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
        # sudo: discuss.channel.rtc.session - creating a session in a test file
        data = {"channel_id": self.channel_channel_group_1.id, "channel_member_id": member_2.id}
        session = self.env["discuss.channel.rtc.session"].sudo().create(data)
        member_0.rtc_inviting_session_id = session

    @users('emp')
    @warmup
    def test_init_store_data(self):
        """Test performance of `init_messaging`."""
        self._setup_test()
        self.maxDiff = None
        self.env.flush_all()
        self.env.invalidate_all()
        store = Store()
        with self.assertQueryCount(emp=self._query_count_init_store):
            self.env["res.users"].with_user(self.users[0])._init_store_data(store)
        self.assertEqual(store.get_result(), self._get_init_store_data_result())

    def _get_init_store_data_result(self):
        """Returns the result of a call to init_messaging.
        The point of having a separate getter is to allow it to be overriden.
        """
        xmlid_to_res_id = self.env["ir.model.data"]._xmlid_to_res_id
        return {
            "Persona": [
                {
                    "active": False,
                    "email": "odoobot@example.com",
                    "id": self.user_root.partner_id.id,
                    "im_status": "bot",
                    "isInternalUser": True,
                    "is_company": False,
                    "name": "OdooBot",
                    "out_of_office_date_end": False,
                    "type": "partner",
                    "userId": self.user_root.id,
                    "write_date": fields.Datetime.to_string(self.user_root.partner_id.write_date),
                },
                {
                    "id": self.users[0].partner_id.id,
                    "isAdmin": False,
                    "isInternalUser": True,
                    "name": "Ernest Employee",
                    "notification_preference": "inbox",
                    "type": "partner",
                    "userId": self.users[0].id,
                    "write_date": fields.Datetime.to_string(self.users[0].partner_id.write_date),
                },
            ],
            "Store": {
                "channel_types_with_seen_infos": sorted(["chat", "group", "livechat"]),
                "action_discuss_id": xmlid_to_res_id("mail.action_discuss"),
                "hasGifPickerFeature": False,
                "hasLinkPreviewFeature": True,
                "has_access_livechat": False,
                "hasMessageTranslationFeature": False,
                "internalUserGroupId": self.env.ref("base.group_user").id,
                "mt_comment_id": xmlid_to_res_id("mail.mt_comment"),
                "odoobot": {"id": self.user_root.partner_id.id, "type": "partner"},
                "self": {"id": self.users[0].partner_id.id, "type": "partner"},
                "settings": {
                    "channel_notifications": False,
                    "mute_until_dt": False,
                    "id": self.env["res.users.settings"]._find_or_create_for_user(self.users[0]).id,
                    "is_discuss_sidebar_category_channel_open": True,
                    "is_discuss_sidebar_category_chat_open": True,
                    "livechat_lang_ids": [],
                    "livechat_username": False,
                    "push_to_talk_key": False,
                    "use_push_to_talk": False,
                    "user_id": {"id": self.users[0].id},
                    "voice_active_duration": 200,
                    "volumes": [("ADD", [])],
                },
            },
        }

    @users('emp')
    @warmup
    def test_init_messaging(self):
        """Test performance of `init_messaging`."""
        self._setup_test()
        self.maxDiff = None
        self.env.flush_all()
        self.env.invalidate_all()
        self.authenticate(self.users[0].login, self.password)
        self.env['res.lang']._get_data(code='en_US')  # cache language for validation
        with self.assertQueryCount(emp=self._query_count):
            init_messaging = self.make_jsonrpc_request("/mail/action", {"init_messaging": {}})
        self.assertEqual(init_messaging, self._get_init_messaging_result())

    def _get_init_messaging_result(self):
        """Returns the result of a call to init_messaging.
        The point of having a separate getter is to allow it to be overriden.
        """
        # sudo: bus.bus: reading non-sensitive last id
        bus_last_id = self.env["bus.bus"].sudo()._bus_last_id()
        return {
            "ChannelMember": [
                self._expected_result_for_channel_member(self.channel_channel_group_1, self.users[2].partner_id),
                self._expected_result_for_channel_member(self.channel_channel_group_1, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_1, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_1, self.users[14].partner_id),
            ],
            "Persona": [
                self._expected_result_for_persona(self.users[2], only_inviting=True),
                self._expected_result_for_persona(self.users[0]),
                self._expected_result_for_persona(self.users[14]),
            ],
            "RtcSession": [
                self._expected_result_for_rtc_session(self.channel_channel_group_1, self.users[2]),
            ],
            "Store": {
                "inbox": {
                    "counter": 1,
                    "counter_bus_id": bus_last_id,
                    "id": "inbox",
                    "model": "mail.box",
                },
                "starred":
                {
                    "counter": 1,
                    "counter_bus_id": bus_last_id,
                    "id": "starred",
                    "model": "mail.box",
                },
                "initChannelsUnreadCounter": 1,
                "odoobotOnboarding": False,
            },
            "Thread": [
                self._expected_result_for_channel(self.channel_channel_group_1),
                self._expected_result_for_channel(self.channel_chat_1),
            ],
        }

    @users("emp")
    @warmup
    def test_discuss_channels(self):
        """Test performance of `/mail/data` with `channels_as_member=True`."""
        self._setup_test()
        self.maxDiff = None
        self.env.flush_all()
        self.env.invalidate_all()
        self.authenticate(self.users[0].login, self.password)
        self.env['res.lang']._get_data(code='en_US')  # cache language for validation
        with self.assertQueryCount(emp=self._query_count_discuss_channels):
            discuss_channels = self.make_jsonrpc_request("/mail/data", {"channels_as_member": True})
        self.assertEqual(discuss_channels, self._get_discuss_channels_result())

    def _get_discuss_channels_result(self):
        """Returns the result of a call to `/mail/data` with `channels_as_member=True`.
        The point of having a separate getter is to allow it to be overriden.
        """
        return {
            "ChannelMember": [
                self._expected_result_for_channel_member(self.channel_channel_group_1, self.users[2].partner_id),
                self._expected_result_for_channel_member(self.channel_general, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_channel_public_1, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_channel_public_2, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_channel_group_1, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_channel_group_2, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_group_1, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_group_1, self.users[12].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_1, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_1, self.users[14].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_2, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_2, self.users[15].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_3, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_3, self.users[2].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_4, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_chat_4, self.users[3].partner_id),
                self._expected_result_for_channel_member(self.channel_livechat_1, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_livechat_1, self.users[1].partner_id),
                self._expected_result_for_channel_member(self.channel_livechat_2, self.users[0].partner_id),
                self._expected_result_for_channel_member(self.channel_livechat_2, guest=True),
            ],
            "Message": [
                self._expected_result_for_message(self.channel_channel_public_1),
                self._expected_result_for_message(self.channel_channel_public_2),
                self._expected_result_for_message(self.channel_channel_group_1),
                self._expected_result_for_message(self.channel_channel_group_2),
                self._expected_result_for_message(self.channel_livechat_1),
                self._expected_result_for_message(self.channel_livechat_2),
            ],
            "Notification": [
                self._expected_result_for_notification(self.channel_channel_public_1),
            ],
            "Persona": [
                self._expected_result_for_persona(self.users[2]),
                self._expected_result_for_persona(
                    self.users[0],
                    also_livechat=True,
                    also_notification=True,
                ),
                self._expected_result_for_persona(self.users[12]),
                self._expected_result_for_persona(self.users[14]),
                self._expected_result_for_persona(self.users[15]),
                self._expected_result_for_persona(self.users[3]),
                self._expected_result_for_persona(self.users[1]),
                self._expected_result_for_persona(guest=True),
            ],
            "RtcSession": [
                self._expected_result_for_rtc_session(self.channel_channel_group_1, self.users[2]),
            ],
            "Thread": [
                self._expected_result_for_channel(self.channel_general),
                self._expected_result_for_channel(self.channel_channel_public_1, has_message=True),
                self._expected_result_for_channel(self.channel_channel_public_2, has_message=True),
                self._expected_result_for_channel(self.channel_channel_group_1, has_message=True),
                self._expected_result_for_channel(self.channel_channel_group_2, has_message=True),
                self._expected_result_for_channel(self.channel_group_1),
                self._expected_result_for_channel(self.channel_chat_1),
                self._expected_result_for_channel(self.channel_chat_2),
                self._expected_result_for_channel(self.channel_chat_3),
                self._expected_result_for_channel(self.channel_chat_4),
                self._expected_result_for_channel(self.channel_livechat_1, has_message=True),
                self._expected_result_for_channel(self.channel_livechat_2, has_message=True),
            ],
        }

    def _expected_result_for_channel(self, channel, has_message=False):
        # sudo: bus.bus: reading non-sensitive last id
        bus_last_id = self.env["bus.bus"].sudo()._bus_last_id()
        members = channel.channel_member_ids
        member_0 = members.filtered(lambda m: m.partner_id == self.users[0].partner_id)
        member_2 = members.filtered(lambda m: m.partner_id == self.users[2].partner_id)
        last_interest_dt = fields.Datetime.to_string(channel.last_interest_dt)
        if channel == self.channel_general:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": self.group_user.full_name,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "channel",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": len(self.group_user.users),
                "model": "discuss.channel",
                "create_uid": self.user_root.id,
                "defaultDisplayMode": False,
                "description": "General announcements for all employees.",
                "group_based_subscription": True,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": False,
                "message_needaction_counter": 0,
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "general",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_channel_public_1:
            res = {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "channel",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 5,
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
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "public channel 1",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
            if has_message:
                res["module_icon"] = "/mail/static/description/icon.png"
            return res
        if channel == self.channel_channel_public_2:
            res = {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "channel",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 5,
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
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "public channel 2",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
            if has_message:
                res["module_icon"] = "/mail/static/description/icon.png"
            return res
        if channel == self.channel_channel_group_1:
            res = {
                "allow_public_upload": False,
                "authorizedGroupFullName": self.group_user.full_name,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "channel",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 5,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", [{"id": member_0.id}]]],
                "is_editable": True,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "message_needaction_counter": 0,
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "group restricted channel 1",
                # sudo: discuss.channel.rtc.session - reading a session in a test file
                "rtcInvitingSession": {"id": member_2.sudo().rtc_session_ids.id},
                # sudo: discuss.channel.rtc.session - reading a session in a test file
                "rtcSessions": [["ADD", [{"id": member_2.sudo().rtc_session_ids.id}]]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
            if has_message:
                res["module_icon"] = "/mail/static/description/icon.png"
            return res
        if channel == self.channel_channel_group_2:
            res = {
                "allow_public_upload": False,
                "authorizedGroupFullName": self.group_user.full_name,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "channel",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 5,
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
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "group restricted channel 2",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
            if has_message:
                res["module_icon"] = "/mail/static/description/icon.png"
            return res
        if channel == self.channel_group_1:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "group",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 2,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": True,
                "is_pinned": True,
                "last_interest_dt": False,
                "message_needaction_counter": 0,
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_chat_1:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "chat",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 2,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": False,
                "message_needaction_counter": 0,
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "Ernest Employee, test14",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "open",
                "uuid": channel.uuid,
            }
        if channel == self.channel_chat_2:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "chat",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 2,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": False,
                "message_needaction_counter": 0,
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "Ernest Employee, test15",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_chat_3:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "chat",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 2,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": False,
                "message_needaction_counter": 0,
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "Ernest Employee, test2",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_chat_4:
            return {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": False,
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "chat",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 2,
                "model": "discuss.channel",
                "create_uid": self.env.user.id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": False,
                "message_needaction_counter": 0,
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "Ernest Employee, test3",
                "rtcSessions": [["ADD", []]],
                "custom_notifications": False,
                "mute_until_dt": False,
                "state": "closed",
                "uuid": channel.uuid,
            }
        if channel == self.channel_livechat_1:
            res = {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": {
                    "code": "IN",
                    "id": self.env.ref("base.in").id,
                    "name": "India",
                },
                "anonymous_name": False,
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "livechat",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 2,
                "model": "discuss.channel",
                "create_uid": self.users[1].id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "livechatChannel": {"id": self.im_livechat_channel.id, "name": "support"},
                "message_needaction_counter": 0,
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "test1 Ernest Employee",
                "custom_notifications": False,
                "mute_until_dt": False,
                "operator": {"id": self.users[0].partner_id.id, "type": "partner"},
                "rtcSessions": [["ADD", []]],
                "state": "closed",
                "uuid": channel.uuid,
            }
            if has_message:
                res["module_icon"] = "/mail/static/description/icon.png"
            return res
        if channel == self.channel_livechat_2:
            res = {
                "allow_public_upload": False,
                "authorizedGroupFullName": False,
                "anonymous_country": {
                    "id": self.env.ref("base.be").id,
                    "code": "BE",
                    "name": "Belgium",
                },
                "anonymous_name": "anon 2",
                "avatarCacheKey": channel.avatar_cache_key,
                "channel_type": "livechat",
                "custom_channel_name": False,
                "fetchChannelInfoState": "fetched",
                "id": channel.id,
                "memberCount": 2,
                "model": "discuss.channel",
                "create_uid": self.env.ref("base.public_user").id,
                "defaultDisplayMode": False,
                "description": False,
                "group_based_subscription": False,
                "invitedMembers": [["ADD", []]],
                "is_editable": False,
                "is_pinned": True,
                "last_interest_dt": last_interest_dt,
                "livechatChannel": {"id": self.im_livechat_channel.id, "name": "support"},
                "message_needaction_counter": 0,
                "message_needaction_counter_bus_id": bus_last_id,
                "name": "anon 2 Ernest Employee",
                "custom_notifications": False,
                "mute_until_dt": False,
                "operator": {"id": self.users[0].partner_id.id, "type": "partner"},
                "rtcSessions": [["ADD", []]],
                "state": "closed",
                "uuid": channel.uuid,
            }
            if has_message:
                res["module_icon"] = "/mail/static/description/icon.png"
            return res
        return {}

    def _expected_result_for_channel_member(self, channel, partner=None, guest=None):
        members = channel.channel_member_ids
        member_0 = members.filtered(lambda m: m.partner_id == self.users[0].partner_id)
        member_0_last_interest_dt = fields.Datetime.to_string(member_0.last_interest_dt)
        member_0_last_seen_dt = fields.Datetime.to_string(member_0.last_seen_dt)
        member_0_create_date = fields.Datetime.to_string(member_0.create_date)
        member_1 = members.filtered(lambda m: m.partner_id == self.users[1].partner_id)
        member_2 = members.filtered(lambda m: m.partner_id == self.users[2].partner_id)
        member_3 = members.filtered(lambda m: m.partner_id == self.users[3].partner_id)
        member_12 = members.filtered(lambda m: m.partner_id == self.users[12].partner_id)
        member_14 = members.filtered(lambda m: m.partner_id == self.users[14].partner_id)
        member_15 = members.filtered(lambda m: m.partner_id == self.users[15].partner_id)
        last_message = channel._get_last_messages()
        member_g = members.filtered(lambda m: m.guest_id)
        guest = member_g.guest_id
        # sudo: bus.bus: reading non-sensitive last id
        bus_last_id = self.env["bus.bus"].sudo()._bus_last_id()
        if channel == self.channel_general and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": False,
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": 0,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_channel_public_1 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": {"id": last_message.id},
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": last_message.id + 1,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": {"id": last_message.id},
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_channel_public_2 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": {"id": last_message.id},
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": last_message.id + 1,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": {"id": last_message.id},
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_channel_group_1 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": {"id": last_message.id},
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": last_message.id + 1,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": {"id": last_message.id},
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_channel_group_1 and partner == self.users[2].partner_id:
            return {
                "id": member_2.id,
                "persona": {"id": self.users[2].partner_id.id, "type": "partner"},
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_channel_group_2 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": {"id": last_message.id},
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": last_message.id + 1,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": {"id": last_message.id},
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_group_1 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": False,
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": 0,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_group_1 and partner == self.users[12].partner_id:
            return {
                "create_date": fields.Datetime.to_string(member_12.create_date),
                "last_seen_dt": False,
                "fetched_message_id": False,
                "id": member_12.id,
                "persona": {"id": self.users[12].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_chat_1 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": False,
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": 0,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_chat_1 and partner == self.users[14].partner_id:
            return {
                "create_date": fields.Datetime.to_string(member_14.create_date),
                "last_seen_dt": False,
                "fetched_message_id": False,
                "id": member_14.id,
                "persona": {"id": self.users[14].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_chat_2 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": False,
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": 0,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_chat_2 and partner == self.users[15].partner_id:
            return {
                "create_date": fields.Datetime.to_string(member_15.create_date),
                "last_seen_dt": False,
                "fetched_message_id": False,
                "id": member_15.id,
                "persona": {"id": self.users[15].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_chat_3 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": False,
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": 0,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_chat_3 and partner == self.users[2].partner_id:
            return {
                "create_date": fields.Datetime.to_string(member_2.create_date),
                "last_seen_dt": False,
                "fetched_message_id": False,
                "id": member_2.id,
                "persona": {"id": self.users[2].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_chat_4 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": False,
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": 0,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_chat_4 and partner == self.users[3].partner_id:
            return {
                "create_date": fields.Datetime.to_string(member_3.create_date),
                "last_seen_dt": False,
                "fetched_message_id": False,
                "id": member_3.id,
                "persona": {"id": self.users[3].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_livechat_1 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": False,
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 0,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": 0,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_livechat_1 and partner == self.users[1].partner_id:
            return {
                "create_date": fields.Datetime.to_string(member_1.create_date),
                "last_seen_dt": fields.Datetime.to_string(member_1.last_seen_dt),
                "fetched_message_id": {"id": last_message.id},
                "id": member_1.id,
                "persona": {"id": self.users[1].partner_id.id, "type": "partner"},
                "seen_message_id": {"id": last_message.id},
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_livechat_2 and partner == self.users[0].partner_id:
            return {
                "create_date": member_0_create_date,
                "fetched_message_id": False,
                "id": member_0.id,
                "last_interest_dt": member_0_last_interest_dt,
                "message_unread_counter": 1,
                "message_unread_counter_bus_id": bus_last_id,
                "last_seen_dt": member_0_last_seen_dt,
                "new_message_separator": 0,
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
                "seen_message_id": False,
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        if channel == self.channel_livechat_2 and guest:
            return {
                "create_date": fields.Datetime.to_string(member_g.create_date),
                "last_seen_dt": fields.Datetime.to_string(member_g.last_seen_dt),
                "fetched_message_id": {"id": last_message.id},
                "id": member_g.id,
                "persona": {"id": guest.id, "type": "guest"},
                "seen_message_id": {"id": last_message.id},
                "thread": {"id": channel.id, "model": "discuss.channel"},
            }
        return {}

    def _expected_result_for_message(self, channel):
        last_message = channel._get_last_messages()
        create_date = fields.Datetime.to_string(last_message.create_date)
        date = fields.Datetime.to_string(last_message.date)
        write_date = fields.Datetime.to_string(last_message.write_date)
        user_0 = self.users[0]
        user_1 = self.users[1]
        user_2 = self.users[2]
        user_9 = self.users[9]
        user_12 = self.users[12]
        user_13 = self.users[13]
        members = channel.channel_member_ids
        member_g = members.filtered(lambda m: m.guest_id)
        guest = member_g.guest_id
        if channel == self.channel_channel_public_1:
            return {
                "attachments": [],
                "author": {"id": user_2.partner_id.id, "type": "partner"},
                "body": "<p>test</p>",
                "create_date": create_date,
                "date": date,
                "default_subject": "public channel 1",
                "email_from": '"test2" <test2@example.com>',
                "id": last_message.id,
                "is_discussion": False,
                "is_note": True,
                "linkPreviews": [],
                "message_type": "comment",
                "model": "discuss.channel",
                "needaction": True,
                "notifications": [{"id": last_message.notification_ids.id}],
                "thread": {"id": channel.id, "model": "discuss.channel"},
                "parentMessage": False,
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
                "starred": True,
                "subject": False,
                "subtype_description": False,
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_channel_public_2:
            return {
                "attachments": [],
                "author": {"id": user_0.partner_id.id, "type": "partner"},
                "body": f'<div class="o_mail_notification">invited <a href="#" data-oe-model="res.partner" data-oe-id="{user_9.partner_id.id}">test9</a> to the channel</div>',
                "create_date": create_date,
                "date": date,
                "default_subject": "public channel 2",
                "email_from": '"Ernest Employee" <e.e@example.com>',
                "id": last_message.id,
                "is_discussion": True,
                "is_note": False,
                "linkPreviews": [],
                "message_type": "notification",
                "model": "discuss.channel",
                "needaction": False,
                "notifications": [],
                "thread": {"id": channel.id, "model": "discuss.channel"},
                "parentMessage": False,
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "public channel 2",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "starred": False,
                "subject": False,
                "subtype_description": False,
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_channel_group_1:
            return {
                "attachments": [],
                "author": {"id": user_0.partner_id.id, "type": "partner"},
                "body": f'<div class="o_mail_notification">invited <a href="#" data-oe-model="res.partner" data-oe-id="{user_12.partner_id.id}">test12</a> to the channel</div>',
                "create_date": create_date,
                "date": date,
                "default_subject": "group restricted channel 1",
                "email_from": '"Ernest Employee" <e.e@example.com>',
                "id": last_message.id,
                "is_discussion": True,
                "is_note": False,
                "linkPreviews": [],
                "message_type": "notification",
                "model": "discuss.channel",
                "needaction": False,
                "notifications": [],
                "thread": {"id": channel.id, "model": "discuss.channel"},
                "parentMessage": False,
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "group restricted channel 1",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "starred": False,
                "subject": False,
                "subtype_description": False,
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_channel_group_2:
            return {
                "attachments": [],
                "author": {"id": user_0.partner_id.id, "type": "partner"},
                "body": f'<div class="o_mail_notification">invited <a href="#" data-oe-model="res.partner" data-oe-id="{user_13.partner_id.id}">test13</a> to the channel</div>',
                "create_date": create_date,
                "date": date,
                "default_subject": "group restricted channel 2",
                "email_from": '"Ernest Employee" <e.e@example.com>',
                "id": last_message.id,
                "is_discussion": True,
                "is_note": False,
                "linkPreviews": [],
                "message_type": "notification",
                "model": "discuss.channel",
                "needaction": False,
                "notifications": [],
                "thread": {"id": channel.id, "model": "discuss.channel"},
                "parentMessage": False,
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "group restricted channel 2",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "starred": False,
                "subject": False,
                "subtype_description": False,
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_livechat_1:
            return {
                "attachments": [],
                "author": {"id": user_1.partner_id.id, "type": "partner"},
                "body": "<p>test</p>",
                "create_date": create_date,
                "date": date,
                "default_subject": "test1 Ernest Employee",
                "id": last_message.id,
                "is_discussion": False,
                "is_note": True,
                "linkPreviews": [],
                "message_type": "notification",
                "model": "discuss.channel",
                "needaction": False,
                "notifications": [],
                "thread": {"id": channel.id, "model": "discuss.channel"},
                "parentMessage": False,
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "test1 Ernest Employee",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "starred": False,
                "subject": False,
                "subtype_description": False,
                "trackingValues": [],
                "write_date": write_date,
            }
        if channel == self.channel_livechat_2:
            return {
                "attachments": [],
                "author": {"id": guest.id, "type": "guest"},
                "body": "<p>test</p>",
                "create_date": create_date,
                "date": date,
                "default_subject": "anon 2 Ernest Employee",
                "email_from": False,
                "id": last_message.id,
                "is_discussion": False,
                "is_note": True,
                "linkPreviews": [],
                "message_type": "comment",
                "model": "discuss.channel",
                "needaction": False,
                "notifications": [],
                "thread": {"id": channel.id, "model": "discuss.channel"},
                "parentMessage": False,
                "pinned_at": False,
                "reactions": [],
                "recipients": [],
                "record_name": "anon 2 Ernest Employee",
                "res_id": channel.id,
                "scheduledDatetime": False,
                "starred": False,
                "subject": False,
                "subtype_description": False,
                "trackingValues": [],
                "write_date": write_date,
            }
        return {}

    def _expected_result_for_notification(self, channel):
        last_message = channel._get_last_messages()
        if channel == self.channel_channel_public_1:
            return {
                "failure_type": False,
                "id": last_message.notification_ids.id,
                "message": {"id": last_message.id},
                "notification_status": "sent",
                "notification_type": "inbox",
                "persona": {"id": self.users[0].partner_id.id, "type": "partner"},
            }
        return {}

    def _expected_result_for_persona(
        self,
        user=None,
        guest=None,
        only_inviting=False,
        also_livechat=False,
        also_notification=False,
    ):
        if user == self.users[0]:
            res = {
                "active": True,
                "email": "e.e@example.com",
                "id": user.partner_id.id,
                "im_status": "online",
                "is_company": False,
                "isInternalUser": True,
                "name": "Ernest Employee",
                "out_of_office_date_end": False,
                "type": "partner",
                "userId": user.id,
                "write_date": fields.Datetime.to_string(user.partner_id.write_date),
            }
            if also_livechat:
                res.update(
                    {
                        "country": False,
                        "is_bot": False,
                        "is_public": False,
                    }
                )
            if also_notification:
                res["displayName"] = "Ernest Employee"
            return res
        if user == self.users[1]:
            return {
                "active": True,
                "country": {
                    "code": "IN",
                    "id": self.env.ref("base.in").id,
                    "name": "India",
                },
                "id": user.partner_id.id,
                "isInternalUser": True,
                "is_bot": False,
                "is_company": False,
                "is_public": False,
                "name": "test1",
                "type": "partner",
                "userId": user.id,
                "write_date": fields.Datetime.to_string(user.partner_id.write_date),
            }
        if user == self.users[2]:
            if only_inviting:
                return {
                    "id": user.partner_id.id,
                    "im_status": "offline",
                    "name": "test2",
                    "type": "partner",
                }
            return {
                "active": True,
                "email": "test2@example.com",
                "id": user.partner_id.id,
                "im_status": "offline",
                "is_company": False,
                "isInternalUser": True,
                "name": "test2",
                "out_of_office_date_end": False,
                "type": "partner",
                "userId": user.id,
                "write_date": fields.Datetime.to_string(user.partner_id.write_date),
            }
        if user == self.users[3]:
            return {
                "active": True,
                "email": False,
                "id": user.partner_id.id,
                "im_status": "offline",
                "is_company": False,
                "isInternalUser": True,
                "name": "test3",
                "out_of_office_date_end": False,
                "type": "partner",
                "userId": user.id,
                "write_date": fields.Datetime.to_string(self.users[3].partner_id.write_date),
            }
        if user == self.users[12]:
            return {
                "active": True,
                "email": False,
                "id": user.partner_id.id,
                "im_status": "offline",
                "is_company": False,
                "isInternalUser": True,
                "name": "test12",
                "out_of_office_date_end": False,
                "type": "partner",
                "userId": user.id,
                "write_date": fields.Datetime.to_string(user.partner_id.write_date),
            }
        if user == self.users[14]:
            return {
                "active": True,
                "email": False,
                "id": user.partner_id.id,
                "im_status": "offline",
                "is_company": False,
                "isInternalUser": True,
                "name": "test14",
                "out_of_office_date_end": False,
                "type": "partner",
                "userId": user.id,
                "write_date": fields.Datetime.to_string(user.partner_id.write_date),
            }
        if user == self.users[15]:
            return {
                "active": True,
                "email": False,
                "id": user.partner_id.id,
                "im_status": "offline",
                "is_company": False,
                "isInternalUser": True,
                "name": "test15",
                "out_of_office_date_end": False,
                "type": "partner",
                "userId": user.id,
                "write_date": fields.Datetime.to_string(user.partner_id.write_date),
            }
        if guest:
            return {
                "id": self.guest.id,
                "im_status": "offline",
                "name": "Visitor",
                "type": "guest",
                "write_date": fields.Datetime.to_string(self.guest.write_date),
            }
        return {}

    def _expected_result_for_rtc_session(self, channel, user):
        members = channel.channel_member_ids
        member_2 = members.filtered(lambda m: m.partner_id == self.users[2].partner_id)
        if channel == self.channel_channel_group_1 and user == self.users[2]:
            return {
                # sudo: discuss.channel.rtc.session - reading a session in a test file
                "channelMember": {"id": member_2.id},
                "id": member_2.sudo().rtc_session_ids.id,
                "isCameraOn": False,
                "isDeaf": False,
                "isScreenSharingOn": False,
                "isSelfMuted": False,
            }
        return {}
