# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial
from odoo.http import route

from odoo.addons.mail.tools.guard_discuss_access import guard_discuss_access
from odoo.tests import HttpCase, tagged, new_test_user, JsonRpcException


@tagged("-at_install", "post_install")
class TestGuardDiscussAccess(HttpCase):
    def test_user_from_same_origin_ok(self):
        new_test_user(self.env, login="test_user", password="Password!1")
        session = self.authenticate("test_user", "Password!1")
        headers = {"Cookie": f"session_id={session.sid};", "Origin": self.base_url()}
        self.assertEqual(self.make_jsonrpc_request("/test_discuss_full/guarded_route_test", headers=headers), "OK")

    def test_user_from_different_origin_ko(self):
        new_test_user(self.env, login="test_user", password="Password!1")
        session = self.authenticate("test_user", "Password!1")
        headers = {"Cookie": f"session_id={session.sid};", "Origin": "http://evil-attacker-website.com"}
        with self.assertRaises(JsonRpcException) as cm:
            self.make_jsonrpc_request("/test_discuss_full/guarded_route_test", headers=headers)
        self.assertEqual(cm.exception.code, 404)

    def test_guest_from_same_origin_ok(self):
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        headers = {"Cookie": f"dgid={guest._format_auth_cookie()};", "Origin": self.base_url()}
        self.assertEqual(self.make_jsonrpc_request("/test_discuss_full/guarded_route_test", headers=headers), "OK")

    def test_guest_from_different_origin_ko(self):
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        headers = {"Cookie": f"dgid={guest._format_auth_cookie()};", "Origin": "http://evil-attacker-website.com"}
        with self.assertRaises(JsonRpcException) as cm:
            self.make_jsonrpc_request("/test_discuss_full/guarded_route_test", headers=headers)
        self.assertEqual(cm.exception.code, 404)

    def test_guest_from_same_origin_via_token_ko(self):
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        headers = {"Origin": self.base_url()}
        with self.assertRaises(JsonRpcException) as cm:
            self.assertEqual(
                self.make_jsonrpc_request(
                    "/test_discuss_full/guarded_route_test", {"guest_token": guest._format_auth_cookie()}, headers=headers
                ),
                "OK",
            )
        self.assertEqual(cm.exception.code, 404)

    def test_guest_from_different_origin_via_token_ok(self):
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        headers = {"Origin": "http://embed-livechat.com"}
        self.assertEqual(
            self.make_jsonrpc_request(
                "/test_discuss_full/guarded_route_test", {"guest_token": guest._format_auth_cookie()}, headers=headers
            ),
            "OK",
        )
