# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase, JsonRpcException


@tagged("post_install", "-at_install")
class TestCorsLivechat(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.operator = cls.env["res.users"].create(
            {
                "name": "Operator",
                "login": "operator",
            }
        )
        cls.env["bus.presence"].create(
            {
                "user_id": cls.operator.id,
                "status": "online",
            }
        )
        cls.livechat_channel = cls.env["im_livechat.channel"].create(
            {"name": "Test Livechat Channel", "user_ids": [cls.operator.id]}
        )

    def test_ignore_user_cookie(self):
        self.authenticate("admin", "admin")
        channel_info = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "anonymous_name": "Visitor",
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
        )
        channel = self.env["discuss.channel"].browse(channel_info["id"])
        self.assertEqual(channel.channel_member_ids[0].partner_id, self.operator.partner_id)
        self.assertFalse(channel.channel_member_ids[1].partner_id)
        self.assertTrue(channel.channel_member_ids[1].guest_id)

    def test_ignore_guest_cookie(self):
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        channel_info = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "anonymous_name": "Visitor",
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
            headers={"Cookie": f"{guest._cookie_name}={guest.id}{guest._cookie_separator}{guest.access_token};"},
        )
        channel = self.env["discuss.channel"].browse(channel_info["id"])
        channel_guest = channel.channel_member_ids.filtered(lambda member: member.guest_id).guest_id
        self.assertNotEqual(channel_guest, guest)

    def test_access_routes_with_valid_guest_token(self):
        channel_info = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "anonymous_name": "Visitor",
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
        )
        self.authenticate(None, None)
        self.make_jsonrpc_request(
            "/im_livechat/cors/channel/messages",
            {
                "guest_token": channel_info["guest_token"],
                "channel_id": channel_info["id"],
            },
        )

    def test_access_denied_for_wrong_channel(self):
        channel_info = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "anonymous_name": "Visitor",
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
        )
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        self.authenticate(None, None)
        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self.make_jsonrpc_request(
                "/im_livechat/cors/channel/messages",
                {
                    "guest_token": guest.access_token,
                    "channel_id": channel_info["id"],
                },
            )
