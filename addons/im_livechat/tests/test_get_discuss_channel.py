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
            channel_operator_ids = [channel_info['operator']['id'] for channel_info in discuss_channels]
            self.assertTrue(all(partner_id in channel_operator_ids for partner_id in self.operators.partner_id.ids))

    def test_channel_get_livechat_visitor_info(self):
        self.maxDiff = None
        belgium = self.env.ref('base.be')
        test_user = self.env['res.users'].create({'name': 'Roger', 'login': 'roger', 'password': self.password, 'country_id': belgium.id})

        # ensure visitor info are correct with anonymous
        operator = self.operators[0]
        with patch('odoo.http.GeoIP.country_code', new_callable=PropertyMock(return_value=belgium.code)):
            data = self.make_jsonrpc_request(
                '/im_livechat/get_session',
                {
                    'anonymous_name': 'Visitor 22',
                    'previous_operator_id': operator.partner_id.id,
                    'channel_id': self.livechat_channel.id,
                    'country_id': belgium.id,
                },
            )
        channel_info = data["discuss.channel"][0]
        self.assertEqual(channel_info['anonymous_name'], "Visitor 22")
        self.assertEqual(channel_info["anonymous_country"], belgium.id)
        self.assertEqual(data["res.country"], [{"code": "BE", "id": belgium.id, "name": "Belgium"}])

        # ensure persona info are hidden (in particular email and real name when livechat username is present)
        channel = self.env["discuss.channel"].browse(channel_info["id"])
        guest = channel.channel_member_ids.guest_id[0]
        self.assertEqual(
            data["mail.guest"],
            [
                {
                    "id": guest.id,
                    "im_status": "offline",
                    "name": "Visitor",
                    "write_date": fields.Datetime.to_string(guest.write_date),
                },
            ],
        )
        self.assertEqual(
            data["res.partner"],
            self._filter_partners_fields(
                {
                    "active": True,
                    "country": False,
                    "id": operator.partner_id.id,
                    "is_public": False,
                    "user_livechat_username": "Michel Operator",
                    "write_date": fields.Datetime.to_string(operator.write_date),
                },
                {
                    "active": False,
                    "id": self.user_root.partner_id.id,
                    "im_status": "bot",
                    "isInternalUser": True,
                    "is_company": False,
                    "name": "OdooBot",
                    "out_of_office_date_end": False,
                    "userId": self.user_root.id,
                    "write_date": fields.Datetime.to_string(self.user_root.partner_id.write_date),
                },
            ),
        )

        # ensure visitor info are correct with real user
        self.authenticate(test_user.login, self.password)
        data = self.make_jsonrpc_request('/im_livechat/get_session', {
            'anonymous_name': 'whatever',
            'previous_operator_id': operator.partner_id.id,
            'user_id': test_user.id,
            'channel_id': self.livechat_channel.id,
        })
        channel_info = data["discuss.channel"][0]
        self.assertFalse(channel_info['anonymous_name'])
        self.assertEqual(channel_info["anonymous_country"], belgium.id)
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
                    "active": True,
                    "country": False,
                    "id": operator.partner_id.id,
                    "is_public": False,
                    "user_livechat_username": "Michel Operator",
                    "write_date": fields.Datetime.to_string(operator.write_date),
                },
                {
                    "active": True,
                    "country": belgium.id,
                    "id": test_user.partner_id.id,
                    "isAdmin": False,
                    "isInternalUser": True,
                    "is_public": False,
                    "name": "Roger",
                    "notification_preference": "email",
                    "signature": str(test_user.signature),
                    "userId": test_user.id,
                    "user_livechat_username": False,
                    "write_date": fields.Datetime.to_string(test_user.write_date),
                },
                {
                    "active": False,
                    "email": "odoobot@example.com",
                    "id": self.user_root.partner_id.id,
                    "im_status": "bot",
                    "isInternalUser": True,
                    "is_company": False,
                    "name": "OdooBot",
                    "out_of_office_date_end": False,
                    "userId": self.user_root.id,
                    "write_date": fields.Datetime.to_string(self.user_root.partner_id.write_date),
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
                    "is_bot": False,
                    "last_seen_dt": False,
                    "persona": {"id": operator.partner_id.id, "type": "partner"},
                    "seen_message_id": False,
                    "thread": {"id": channel_info["id"], "model": "discuss.channel"},
                },
                {
                    "create_date": fields.Datetime.to_string(visitor_member.create_date),
                    "fetched_message_id": False,
                    "id": visitor_member.id,
                    "is_bot": False,
                    "last_interest_dt": fields.Datetime.to_string(visitor_member.last_interest_dt),
                    "last_seen_dt": False,
                    "message_unread_counter": 0,
                    "message_unread_counter_bus_id": self.env["bus.bus"]._bus_last_id() - 1,
                    "new_message_separator": 0,
                    "persona": {"id": test_user.partner_id.id, "type": "partner"},
                    "seen_message_id": False,
                    "thread": {"id": channel_info["id"], "model": "discuss.channel"},
                },
            ],
        )
        self.assertEqual(data["res.country"], [{"code": "BE", "id": belgium.id, "name": "Belgium"}])
        # ensure visitor info are correct when operator is testing themselves
        operator = self.operators[0]
        self.authenticate(operator.login, self.password)
        data = self.make_jsonrpc_request('/im_livechat/get_session', {
            'anonymous_name': 'whatever',
            'previous_operator_id': operator.partner_id.id,
            'user_id': operator.id,
            'channel_id': self.livechat_channel.id,
        })
        channel_info = data["discuss.channel"][0]
        operator_member_domain = [
            ('channel_id', '=', channel_info['id']),
            ('partner_id', '=', operator.partner_id.id),
        ]
        operator_member = self.env['discuss.channel.member'].search(operator_member_domain)
        self.assertEqual(channel_info['operator'], {
            "id": operator.partner_id.id,
            "type": "partner",
        })
        self.assertFalse(channel_info['anonymous_name'])
        self.assertEqual(channel_info['anonymous_country'], False)
        self.assertEqual(
            data["res.partner"],
            self._filter_partners_fields(
                {
                    "active": True,
                    "country": False,
                    "id": operator.partner_id.id,
                    "isAdmin": False,
                    "isInternalUser": True,
                    "is_public": False,
                    "name": "Michel",
                    "notification_preference": "email",
                    "signature": str(operator.signature),
                    "userId": operator.id,
                    "user_livechat_username": "Michel Operator",
                    "write_date": fields.Datetime.to_string(operator.partner_id.write_date),
                },
                {
                    "active": False,
                    "email": "odoobot@example.com",
                    "id": self.user_root.partner_id.id,
                    "im_status": "bot",
                    "isInternalUser": True,
                    "is_company": False,
                    "name": "OdooBot",
                    "out_of_office_date_end": False,
                    "userId": self.user_root.id,
                    "write_date": fields.Datetime.to_string(self.user_root.partner_id.write_date),
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
                    "is_bot": False,
                    "last_interest_dt": fields.Datetime.to_string(operator_member.last_interest_dt),
                    "last_seen_dt": False,
                    "message_unread_counter": 0,
                    "message_unread_counter_bus_id": self.env["bus.bus"]._bus_last_id() - 1,
                    "new_message_separator": 0,
                    "persona": {"id": operator.partner_id.id, "type": "partner"},
                    "seen_message_id": False,
                    "thread": {"id": channel_info["id"], "model": "discuss.channel"},
                },
            ],
        )

    def _open_livechat_discuss_channel(self):
        discuss_channels = []
        for _i in range(5):
            data = self.make_jsonrpc_request('/im_livechat/get_session', {'anonymous_name': 'Anonymous', 'channel_id': self.livechat_channel.id})
            discuss_channels.append(data["discuss.channel"][0])
            # send a message to mark this channel as 'active'
            self.env["discuss.channel"].browse(data["discuss.channel"][0]["id"]).message_post(
                body="cc"
            )
        return discuss_channels

    def test_channel_not_pinned_for_operator_before_first_message(self):
        operator = self.operators[0]
        params = {
            "anonymous_name": "whatever",
            "channel_id": self.livechat_channel.id,
            "previous_operator_id": operator.partner_id.id
        }
        channel_id = self.make_jsonrpc_request("/im_livechat/get_session", params)[
            "discuss.channel"
        ][0]["id"]
        member_domain = [("channel_id", "=", channel_id), ("is_self", "=", True)]
        member = self.env["discuss.channel.member"].with_user(operator).search(member_domain)
        self.assertEqual(len(member), 1, "operator should be member of channel")
        self.assertFalse(member.is_pinned, "channel should not be pinned for operator initially")
        self.env["discuss.channel"].browse(channel_id).message_post(body="cc")
        self.assertTrue(member.is_pinned, "channel should be pinned for operator after visitor sent a message")
        self.authenticate(operator.login, self.password)
        operator_channels = self.make_jsonrpc_request("/mail/data", {"channels_as_member": True})[
            "discuss.channel"
        ]
        channel_ids = [channel["id"] for channel in operator_channels]
        self.assertIn(channel_id, channel_ids, "channel should be fetched by operator on new page")

    def test_read_channel_unpined_for_operator_after_one_day(self):
        data = self.make_jsonrpc_request('/im_livechat/get_session', {'anonymous_name': 'visitor', 'channel_id': self.livechat_channel.id})
        member_of_operator = self.env["discuss.channel.member"].search(
            [
                ("channel_id", "=", data["discuss.channel"][0]["id"]),
                ("partner_id", "in", self.operators.partner_id.ids),
            ]
        )
        message = (
            self.env["discuss.channel"]
            .browse(data["discuss.channel"][0]["id"])
            .message_post(body="cc")
        )
        member_of_operator._mark_as_read(message.id)
        with freeze_time(fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=1))):
            member_of_operator._gc_unpin_livechat_sessions()
        self.assertFalse(member_of_operator.is_pinned, "read channel should be unpinned after one day")

    def test_unread_channel_not_unpined_for_operator_after_autovacuum(self):
        data = self.make_jsonrpc_request('/im_livechat/get_session', {'anonymous_name': 'visitor', 'channel_id': self.livechat_channel.id})
        member_of_operator = self.env["discuss.channel.member"].search(
            [
                ("channel_id", "=", data["discuss.channel"][0]["id"]),
                ("partner_id", "in", self.operators.partner_id.ids),
            ]
        )
        self.env["discuss.channel"].browse(data["discuss.channel"][0]["id"]).message_post(body="cc")
        with freeze_time(fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=1))):
            member_of_operator._gc_unpin_livechat_sessions()
        self.assertTrue(member_of_operator.is_pinned, "unread channel should not be unpinned after autovacuum")

    def test_only_active_livechats_returned_by_init_messaging(self):
        self.authenticate(None, None)
        operator = new_test_user(self.env, login="John")
        self.env["bus.presence"].create({"user_id": operator.id, "status": "online"})
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Customer Support", "user_ids": [operator.id]}
        )
        inactive_livechat = self.env["discuss.channel"].browse(
            self.make_jsonrpc_request(
                "/im_livechat/get_session",
                {
                    "anonymous_name": "Visitor",
                    "channel_id": livechat_channel.id,
                    "persisted": True,
                },
            )["discuss.channel"][0]["id"]
        )
        self.make_jsonrpc_request(
            "/im_livechat/visitor_leave_session", {"channel_id": inactive_livechat.id}
        )
        guest = inactive_livechat.channel_member_ids.filtered(lambda m: m.guest_id).guest_id
        non_livechat_channel = self.env['discuss.channel']._create_channel(name="General", group_id=None)
        non_livechat_channel.add_members(guest_ids=guest.ids)
        non_livechat_channel.channel_member_ids.fold_state = "open"
        active_livechat = self.env["discuss.channel"].browse(
            self.make_jsonrpc_request(
                "/im_livechat/get_session",
                {
                    "anonymous_name": "Visitor",
                    "channel_id": livechat_channel.id,
                    "persisted": True,
                },
            )["discuss.channel"][0]["id"]
        )
        init_messaging_result = self.make_jsonrpc_request("/mail/action", {"init_messaging": {}})
        self.assertEqual(len(init_messaging_result["discuss.channel"]), 2)
        self.assertEqual(init_messaging_result["discuss.channel"][0]["channel_type"], "channel")
        self.assertEqual(init_messaging_result["discuss.channel"][1]["channel_type"], "livechat")
        init_messaging_result = self.make_jsonrpc_request("/mail/action", {"init_messaging": {
            "channel_types": ["livechat"],
        }})
        self.assertEqual(len(init_messaging_result["discuss.channel"]), 1)
        self.assertEqual(init_messaging_result["discuss.channel"][0]["id"], active_livechat.id)
