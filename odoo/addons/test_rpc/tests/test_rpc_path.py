import logging

from odoo.tests import Like, get_db_name, tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("-at_install", "post_install")
class TestRpcPath(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.session = cls.authenticate(cls, "demo", "demo")

    def setUp(self):
        super().setUp()
        self.opener.cookies["session_id"] = self.session.sid

    def test_rpc_path_call_button(self):
        with self.assertLogs("odoo.service.http.access", logging.INFO) as capture:
            self.call_jsonrpc(
                "/web/dataset/call_button",
                {
                    "model": "res.users",
                    "method": "read",
                    "args": [self.user_demo.id],
                    "kwargs": {"fields": ["login"]},
                },
            )
        self.assertEqual(
            capture.output,
            [
                Like("...POST /web/dataset/call_button#res.users.read HTTP/..."),
            ],
        )

    def test_rpc_path_call_kw(self):
        with self.assertLogs("odoo.service.http.access", logging.INFO) as capture:
            self.call_jsonrpc(
                "/web/dataset/call_kw",
                {
                    "model": "res.users",
                    "method": "read",
                    "args": [self.user_demo.id],
                    "kwargs": {"fields": ["login"]},
                },
            )
        self.assertEqual(
            capture.output,
            [
                Like("...POST /web/dataset/call_kw#res.users.read HTTP/..."),
            ],
        )

    def test_rpc_path_call_kw_with_path(self):
        with self.assertLogs("odoo.service.http.access", logging.INFO) as capture:
            self.call_jsonrpc(
                "/web/dataset/call_kw/res.users.read",
                {
                    "model": "res.users",
                    "method": "read",
                    "args": [self.user_demo.id],
                    "kwargs": {"fields": ["login"]},
                },
            )
        self.assertEqual(
            capture.output,
            [
                Like("...POST /web/dataset/call_kw/res.users.read HTTP/..."),
            ],
        )

    @mute_logger("odoo.addons.rpc.controllers.xmlrpc")
    def test_rpc_path_xmlrpc(self):
        with self.assertLogs("odoo.service.http.access", logging.INFO) as capture:
            self.xmlrpc_object.execute_kw(
                get_db_name(),
                self.user_demo.id,
                "demo",
                "res.users",
                "read",
                [self.user_demo.id, ["login"]],
            )
        self.assertEqual(
            capture.output,
            [
                Like("...POST /xmlrpc/2/object#res.users.read HTTP/..."),
            ],
        )
