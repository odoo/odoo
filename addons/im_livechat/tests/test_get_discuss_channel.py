# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from freezegun import freeze_time
from unittest.mock import patch, PropertyMock

from odoo import fields
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import new_test_user, tagged


@tagged("post_install", "-at_install")
class TestGetDiscussChannel(TestImLivechatCommon, MailCommon):
    def test_get_discuss_channel(self):
        """For a livechat with 5 available operators, we open 5 channels 5 times (25 channels total).
        For every 5 channels opening, we check that all operators were assigned.
        """

        for _i in range(5):
            discuss_channels = self._open_livechat_discuss_channel()
            channel_operator_ids = [
                channel_info["livechat_operator_id"] for channel_info in discuss_channels
            ]
            self.assertTrue(all(partner_id in channel_operator_ids for partner_id in self.operators.mapped('partner_id').ids))

    def test_channel_get_livechat_visitor_info(self):
        self.maxDiff = None
        belgium = self.env.ref('base.be')
        test_user = self.env['res.users'].create({'name': 'Roger', 'login': 'roger', 'password': self.password, 'country_id': belgium.id})

        # ensure visitor info are correct with anonymous
        operator = self.operators[0]
        with patch('odoo.http.GeoIP.country_code', new_callable=PropertyMock(return_value=belgium.code)):
            data = self.make_jsonrpc_request(
                "/im_livechat/get_session",
                {
                    "previous_operator_id": operator.partner_id.id,
                    "channel_id": self.livechat_channel.id,
                },
            )["store_data"]
        channel_info = data["discuss.channel"][0]
        self.assertEqual(channel_info["name"], "Visitor Michel Operator")
        self.assertEqual(channel_info["country_id"], belgium.id)
        self.assertEqual(data["res.country"], [{"code": "BE", "id": belgium.id, "name": "Belgium"}])

        # ensure persona info are hidden (in particular email and real name when livechat username is present)
        channel = self.env["discuss.channel"].browse(channel_info["id"])
        guest = channel.channel_member_ids.guest_id[0]
        self.assertEqual(
            data["mail.guest"],
            [
                {
                    "avatar_128_access_token": guest._get_avatar_128_access_token(),
                    "country_id": belgium.id,
                    "id": guest.id,
                    "im_status": "offline",
                    "im_status_access_token": guest._get_im_status_access_token(),
                    "name": "Visitor",
                    "offline_since": False,
                    "write_date": fields.Datetime.to_string(guest.write_date),
                },
            ],
        )
        self.assertEqual(
            data["res.partner"],
            self._filter_partners_fields(
              {
                    "active": False,
                    "avatar_128_access_token": self.partner_root._get_avatar_128_access_token(),
                    "id": self.user_root.partner_id.id,
                    "im_status": "bot",
                    "im_status_access_token": self.partner_root._get_im_status_access_token(),
                    "is_company": False,
                    "main_user_id": self.user_root.id,
                    "name": "OdooBot",
                    "write_date": fields.Datetime.to_string(self.user_root.partner_id.write_date),
                },
                {
                    "active": True,
                    "avatar_128_access_token": operator.partner_id._get_avatar_128_access_token(),
                    "country_id": False,
                    "id": operator.partner_id.id,
                    "im_status": "offline",
                    "im_status_access_token": operator.partner_id._get_im_status_access_token(),
                    "is_public": False,
                    "mention_token": operator.partner_id._get_mention_token(),
                    "user_livechat_username": "Michel Operator",
                    "write_date": fields.Datetime.to_string(operator.write_date),
                },
            ),
        )
        self.assertEqual(
            data["res.users"],
            self._filter_users_fields(
                {"id": self.user_root.id, "share": False},
            ),
        )
        # ensure visitor info are correct with real user
        self.authenticate(test_user.login, self.password)
        data = self.make_jsonrpc_request('/im_livechat/get_session', {
            'previous_operator_id': operator.partner_id.id,
            'channel_id': self.livechat_channel.id,
        })["store_data"]
        channel_info = data["discuss.channel"][0]
        self.assertEqual(channel_info["name"], "Roger Michel Operator")
        self.assertEqual(channel_info["country_id"], belgium.id)
        self.assertEqual(data["res.country"], [{"code": "BE", "id": belgium.id, "name": "Belgium"}])
        operator_member_domain = [
            ('channel_id', '=', channel_info['id']),
            ('partner_id', '=', operator.partner_id.id),
        ]
        operator_member = self.env['discuss.channel.member'].search(operator_member_domain)
        visitor_member_domain = [
            ('channel_id', '=', channel_info['id']),
            ('partner_id', '=', test_user.partner_id.id),
        ]
        visitor_member = self.env['discuss.channel.member'].search(visitor_member_domain)
        self.assertEqual(
            data["res.partner"],
            self._filter_partners_fields(
                {
                    "active": False,
                    "avatar_128_access_token": self.partner_root._get_avatar_128_access_token(),
                    "email": "odoobot@example.com",
                    "id": self.user_root.partner_id.id,
                    "im_status": "bot",
                    "im_status_access_token": self.partner_root._get_im_status_access_token(),
                    "is_company": False,
                    "main_user_id": self.user_root.id,
                    "name": "OdooBot",
                    "write_date": fields.Datetime.to_string(self.user_root.partner_id.write_date),
                },
                {
                    "active": True,
                    "avatar_128_access_token": test_user.partner_id._get_avatar_128_access_token(),
                    "country_id": belgium.id,
                    "id": test_user.partner_id.id,
                    "im_status": "offline",
                    "im_status_access_token": test_user.partner_id._get_im_status_access_token(),
                    "is_public": False,
                    "main_user_id": test_user.id,
                    "mention_token": test_user.partner_id._get_mention_token(),
                    "name": "Roger",
                    "email": test_user.partner_id.email,
                    "offline_since": False,
                    "user_livechat_username": False,
                    "write_date": fields.Datetime.to_string(test_user.write_date),
                },
               {
                    "active": True,
                    "avatar_128_access_token": operator.partner_id._get_avatar_128_access_token(),
                    "country_id": False,
                    "id": operator.partner_id.id,
                    "im_status": "offline",
                    "im_status_access_token": operator.partner_id._get_im_status_access_token(),
                    "is_public": False,
                    "mention_token": operator.partner_id._get_mention_token(),
                    "user_livechat_username": "Michel Operator",
                    "write_date": fields.Datetime.to_string(operator.write_date),
                },
            ),
        )
        self.assertEqual(
            data["res.users"],
            self._filter_users_fields(
                {"id": self.user_root.id, "employee_ids": [], "share": False},
                {
                    "id": test_user.id,
                    "is_admin": False,
                    "is_livechat_manager": False,
                    "notification_type": "email",
                    "signature": ["markup", str(test_user.signature)],
                    "share": False,
                },
            ),
        )
        self.assertEqual(
            data["discuss.channel.member"],
            [
                {
                    "create_date": fields.Datetime.to_string(operator_member.create_date),
                    "fetched_message_id": False,
                    "id": operator_member.id,
                    "livechat_member_type": "agent",
                    "last_seen_dt": False,
                    "partner_id": operator.partner_id.id,
                    "seen_message_id": False,
                    "channel_id": {"id": channel_info["id"], "model": "discuss.channel"},
                },
                {
                    "create_date": fields.Datetime.to_string(visitor_member.create_date),
                    "custom_channel_name": False,
                    "custom_notifications": False,
                    "fetched_message_id": False,
                    "id": visitor_member.id,
                    "livechat_member_type": "visitor",
                    "last_interest_dt": fields.Datetime.to_string(visitor_member.last_interest_dt),
                    "last_seen_dt": False,
                    "message_unread_counter": 0,
                    "message_unread_counter_bus_id": self.env["bus.bus"]._bus_last_id() - 2,
                    "mute_until_dt": False,
                    "new_message_separator": 0,
                    "partner_id": test_user.partner_id.id,
                    "rtc_inviting_session_id": False,
                    "seen_message_id": False,
                    "unpin_dt": False,
                    "channel_id": {"id": channel_info["id"], "model": "discuss.channel"},
                },
            ],
        )
        self.assertEqual(data["res.country"], [{"code": "BE", "id": belgium.id, "name": "Belgium"}])
        # ensure visitor info are correct when operator is testing themselves
        operator = self.operators[0]
        self.authenticate(operator.login, self.password)
        data = self.make_jsonrpc_request('/im_livechat/get_session', {
            'previous_operator_id': operator.partner_id.id,
            'channel_id': self.livechat_channel.id,
        })["store_data"]
        channel_info = data["discuss.channel"][0]
        operator_member_domain = [
            ('channel_id', '=', channel_info['id']),
            ('partner_id', '=', operator.partner_id.id),
        ]
        operator_member = self.env['discuss.channel.member'].search(operator_member_domain)
        self.assertEqual(channel_info['livechat_operator_id'], operator.partner_id.id)
        self.assertEqual(channel_info["name"], "Michel Michel Operator")
        self.assertEqual(channel_info['country_id'], False)
        self.assertEqual(
            data["res.partner"],
            self._filter_partners_fields(
                {
                    "active": False,
                    "avatar_128_access_token": self.partner_root._get_avatar_128_access_token(),
                    "email": "odoobot@example.com",
                    "id": self.user_root.partner_id.id,
                    "im_status": "bot",
                    "im_status_access_token": self.partner_root._get_im_status_access_token(),
                    "is_company": False,
                    "main_user_id": self.user_root.id,
                    "name": "OdooBot",
                    "write_date": fields.Datetime.to_string(self.user_root.partner_id.write_date),
                },
                {
                    "active": True,
                    "avatar_128_access_token": operator.partner_id._get_avatar_128_access_token(),
                    "country_id": False,
                    "id": operator.partner_id.id,
                    "im_status": "offline",
                    "im_status_access_token": operator.partner_id._get_im_status_access_token(),
                    "is_public": False,
                    "main_user_id": operator.id,
                    "mention_token": operator.partner_id._get_mention_token(),
                    "name": "Michel",
                    "email": operator.email,
                    "user_livechat_username": "Michel Operator",
                    "write_date": fields.Datetime.to_string(operator.partner_id.write_date),
                },
            ),
        )
        self.assertEqual(
            data["discuss.channel.member"],
            [
                {
                    "create_date": fields.Datetime.to_string(operator_member.create_date),
                    "custom_channel_name": False,
                    "custom_notifications": False,
                    "fetched_message_id": False,
                    "id": operator_member.id,
                    "livechat_member_type": "agent",
                    "last_interest_dt": fields.Datetime.to_string(operator_member.last_interest_dt),
                    "last_seen_dt": False,
                    "message_unread_counter": 0,
                    "message_unread_counter_bus_id": self.env["bus.bus"]._bus_last_id() - 2,
                    "mute_until_dt": False,
                    "new_message_separator": 0,
                    "partner_id": operator.partner_id.id,
                    "rtc_inviting_session_id": False,
                    "seen_message_id": False,
                    "unpin_dt": fields.Datetime.to_string(operator_member.unpin_dt),
                    "channel_id": {"id": channel_info["id"], "model": "discuss.channel"},
                },
            ],
        )
        self.assertEqual(
            data["res.users"],
            self._filter_users_fields(
                {"id": self.user_root.id, "employee_ids": [], "share": False},
                {
                    "id": operator.id,
                    "is_admin": False,
                    "is_livechat_manager": False,
                    "notification_type": "email",
                    "share": False,
                    "signature": ["markup", str(operator.signature)],
                },
            ),
        )

    def _open_livechat_discuss_channel(self):
        discuss_channels = []
        for _i in range(5):
            data = self.make_jsonrpc_request(
                "/im_livechat/get_session", {"channel_id": self.livechat_channel.id}
            )
            discuss_channels.append(
                next(
                    filter(
                        lambda c: c["id"] == data["channel_id"],
                        data["store_data"]["discuss.channel"],
                    )
                )
            )
            # send a message to mark this channel as 'active'
            self.env["discuss.channel"].browse(data["channel_id"]).message_post(body="cc")
        return discuss_channels

    def test_channel_not_pinned_for_operator_before_first_message(self):
        operator = self.operators[0]
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "previous_operator_id": operator.partner_id.id,
            },
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        member = channel.with_user(operator).self_member_id
        self.assertEqual(member.partner_id, operator.partner_id, "operator should be member of channel")
        self.assertFalse(member.is_pinned, "channel should not be pinned for operator initially")
        channel.message_post(body="cc", message_type="comment")
        self.assertTrue(member.is_pinned, "channel should be pinned for operator after visitor sent a message")
        self.authenticate(operator.login, self.password)
        data = self.make_jsonrpc_request("/mail/data", {"fetch_params": ["channels_as_member"]})
        channel_ids = [channel["id"] for channel in data["discuss.channel"]]
        self.assertIn(channel.id, channel_ids, "channel should be fetched by operator on new page")

    def test_read_channel_unpined_for_operator_after_one_day(self):
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": self.livechat_channel.id}
        )
        member_of_operator = self.env["discuss.channel.member"].search(
            [
                ("channel_id", "=", data["channel_id"]),
                ("partner_id", "in", self.operators.partner_id.ids),
            ]
        )
        message = self.env["discuss.channel"].browse(data["channel_id"]).message_post(body="cc", message_type="comment")
        member_of_operator._mark_as_read(message.id)
        with freeze_time(fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=1))):
            member_of_operator._gc_unpin_livechat_sessions()
        self.assertFalse(member_of_operator.is_pinned, "read channel should be unpinned after one day")
        self.assertTrue(member_of_operator.channel_id.livechat_end_dt)

    def test_unread_channel_not_unpined_for_operator_after_autovacuum(self):
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": self.livechat_channel.id}
        )
        member_of_operator = self.env["discuss.channel.member"].search(
            [
                ("channel_id", "=", data["channel_id"]),
                ("partner_id", "in", self.operators.partner_id.ids),
            ]
        )
        self.env["discuss.channel"].browse(data["channel_id"]).message_post(body="cc", message_type="comment")
        with freeze_time(fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=1))):
            member_of_operator._gc_unpin_livechat_sessions()
        self.assertTrue(member_of_operator.is_pinned, "unread channel should not be unpinned after autovacuum")
        self.assertFalse(member_of_operator.channel_id.livechat_end_dt)

    def test_livechat_manager_can_invite_anyone(self):
        channel = self.env["discuss.channel"].create(
            {
                "channel_type": "livechat",
                "livechat_operator_id": self.operators[2].partner_id.id,
                "name": "test",
            }
        )
        other_member = channel.with_user(self.operators[0])._add_members(users=self.operators[1])
        self.assertEqual(other_member.partner_id, self.operators[1].partner_id)
        self_member = channel.with_user(self.operators[0])._add_members(users=self.operators[0])
        self.assertEqual(self_member.partner_id, self.operators[0].partner_id)

    def test_livechat_operator_can_see_all_livechat_conversations_and_members(self):
        bob_user = new_test_user(
            self.env, "bob_user", groups="base.group_user,im_livechat.im_livechat_group_user"
        )
        livechat_session = self.env["discuss.channel"].create(
            {
                "channel_type": "livechat",
                "livechat_operator_id": self.operators[0].partner_id.id,
                "name": "test",
            }
        )
        livechat_session.with_user(self.operators[0])._add_members(users=self.operators[1])
        self.assertEqual(
            self.env["discuss.channel"].with_user(bob_user).search([("id", "=", livechat_session.id)]),
            livechat_session
        )
        self.assertEqual(
            self.env["discuss.channel.member"].with_user(bob_user).search([("channel_id", "=", livechat_session.id)]),
            livechat_session.channel_member_ids
        )

    def test_user_prevails_over_guest_when_creating_member(self):
        test_user = new_test_user(self.env, "meow_user")
        guest = self.env["mail.guest"].create({"name": "Guest"})
        self.authenticate(test_user.login, test_user.password)
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": self.livechat_channel.id},
            cookies={guest._cookie_name: guest._format_auth_cookie()},
        )
        channel_members = self.env["discuss.channel"].browse(data["channel_id"]).channel_member_ids
        agent = channel_members.filtered(lambda member: member.livechat_member_type == "agent")
        visitor = channel_members.filtered(lambda member: member.livechat_member_type == "visitor")
        self.assertEqual(len(agent), 1)
        self.assertEqual(len(visitor), 1)
        self.assertEqual(visitor.partner_id, test_user.partner_id)
