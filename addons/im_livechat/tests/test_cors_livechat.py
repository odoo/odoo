# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import Controller, request, route
from odoo.tests import HttpCase, JsonRpcException
from odoo.tools import file_open, mute_logger


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
        cls.env["mail.presence"]._update_presence(cls.operator)
        cls.livechat_channel = cls.env["im_livechat.channel"].create(
            {"name": "Test Livechat Channel", "user_ids": [cls.operator.id]}
        )

    def test_ignore_user_cookie(self):
        self.authenticate("admin", "admin")
        data = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertEqual(channel.create_uid, self.env.ref("base.public_user"))
        self.assertEqual(channel.channel_member_ids[0].partner_id, self.operator.partner_id)
        self.assertFalse(channel.channel_member_ids[1].partner_id)
        self.assertTrue(channel.channel_member_ids[1].guest_id)

    def test_authenticated_session_is_kept(self):
        self.authenticate("admin", "admin")
        self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
        )
        self.assertEqual(
            self.make_jsonrpc_request("/web/session/get_session_info")["uid"],
            self.env.ref("base.user_admin").id,
        )

    def test_ignore_guest_cookie(self):
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        data = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
            cookies={guest._cookie_name: f'{guest.id}{guest._cookie_separator}{guest.access_token}'}
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        channel_guest = channel.channel_member_ids.filtered(lambda member: member.guest_id).guest_id
        self.assertNotEqual(channel_guest, guest)

    def test_access_routes_with_valid_guest_token(self):
        data = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
        )
        self.authenticate(None, None)
        self.make_jsonrpc_request(
            "/im_livechat/cors/channel/mark_as_read",
            {
                "guest_token": data["store_data"]["Store"]["guest_token"],
                "channel_id": data["channel_id"],
                "last_message_id": 0,
            },
        )

    def test_access_route_with_guest_token_in_form_data(self):
        data = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
        )
        self.authenticate(None, None)
        upload_params = {
            "thread_id": data["channel_id"],
            "thread_model": "discuss.channel",
        }
        with file_open("addons/web/__init__.py") as file:
            res = self.url_open(
                "/im_livechat/cors/attachment/upload",
                {**upload_params, "guest_token": data["store_data"]["Store"]["guest_token"]},
                files={"ufile": file},
            )
        res.raise_for_status()
        attachment_id = json.loads(res.content)["data"]["attachment_id"]
        self.assertEqual(self.env["ir.attachment"].browse(attachment_id).res_id, data["channel_id"])
        with mute_logger("odoo.http"), file_open("addons/web/__init__.py") as file:
            res = self.url_open(
                "/im_livechat/cors/attachment/upload", upload_params, files={"ufile": file}
            )
        self.assertEqual(res.status_code, 404)

    def test_body_that_is_not_an_object_is_rejected_by_the_dispatcher(self):
        self.authenticate(None, None)
        for body in ("[]", "not json"):
            with self.subTest(body=body), mute_logger("odoo.http"):
                res = self.url_open(
                    "/im_livechat/cors/init",
                    data=body,
                    headers={"Content-Type": "application/json"},
                )
                self.assertEqual(res.status_code, 400)

    def test_access_denied_for_wrong_channel(self):
        data = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "persisted": True,
            },
        )
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        self.authenticate(None, None)
        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self.make_jsonrpc_request(
                "/im_livechat/cors/channel/mark_as_read",
                {
                    "guest_token": guest.access_token,
                    "channel_id": data["channel_id"],
                    "last_message_id": 0,
                },
            )


class TestJson2GuestToken(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class LivechatJson2Controller(Controller):
            @route("/im_livechat/tests/json2_guest", type="json2", auth="force_guest")
            def json2_guest(self, guest_token=None):
                return request.env["mail.guest"]._get_guest_from_context().id

        cls.env.transaction.invalidate_ormcache("routing")

    def test_the_token_is_read_from_the_top_level_of_the_body(self):
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        token = f"{guest.id}{guest._cookie_separator}{guest.access_token}"
        res = self.url_open(
            "/im_livechat/tests/json2_guest",
            data=json.dumps({"guest_token": token}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(json.loads(res.content), guest.id)
        with mute_logger("odoo.http"):
            res = self.url_open(
                "/im_livechat/tests/json2_guest",
                data="{}",
                headers={"Content-Type": "application/json"},
            )
        self.assertEqual(res.status_code, 404)
