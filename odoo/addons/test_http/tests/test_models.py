import logging
from http import HTTPStatus

import odoo.http
from odoo.tests import get_db_name, tagged
from odoo.tests.common import Like, new_test_user
from odoo.tools import mute_logger
from odoo.tools.misc import submap

from .test_common import TestHttpBase
from odoo.addons.test_http.utils import HtmlTokenizer


@tagged("post_install", "-at_install")
class TestHttpModels(TestHttpBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.jackoneill = new_test_user(cls.env, "jackoneill", context={"lang": "en_US"})

    def setUp(self):
        super().setUp()
        self.authenticate("jackoneill", "jackoneill")

    def test_models0_galaxy_ok(self):
        milky_way = self.env.ref("test_http.milky_way")

        res = self.url_open(f"/test_http/{milky_way.id}")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            HtmlTokenizer.tokenize(res.text),
            HtmlTokenizer.tokenize("""\
                <p>Milky Way</p>
                <ul>
                    <li><a href="/test_http/1/1">Earth (P4X-126)</a></li>
                    <li><a href="/test_http/1/2">Abydos (P2X-125)</a></li>
                    <li><a href="/test_http/1/3">Dakara (P5C-113)</a></li>
                </ul>
                """),
        )

    @mute_logger("odoo.http")
    def test_models1_galaxy_ko(self):
        res = self.url_open("/test_http/404")  # unknown galaxy
        self.assertEqual(res.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertIn("The Ancients did not settle there.", res.text)

    def test_models2_stargate_ok(self):
        milky_way = self.env.ref("test_http.milky_way")
        earth = self.env.ref("test_http.earth")

        res = self.url_open(f"/test_http/{milky_way.id}/{earth.id}")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            HtmlTokenizer.tokenize(res.text),
            HtmlTokenizer.tokenize("""\
                <dl>
                    <dt>name</dt><dd>Earth</dd>
                    <dt>address</dt><dd>sq5Abt</dd>
                    <dt>sgc_designation</dt><dd>P4X-126</dd>
                </dl>
            """),
        )

    def test_models3_stargate_ko(self):
        milky_way = self.env.ref("test_http.milky_way")
        with self.assertLogs("odoo.http.application", level="WARNING") as logs:
            res = self.url_open(f"/test_http/{milky_way.id}/9999")  # unknown gate
        self.assertEqual(res.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertIn("The goauld destroyed the gate", res.text)
        self.assertEqual(
            logs.output,
            ["WARNING:odoo.http.application:The goauld destroyed the gate"],
        )

    def test_models4_stargate_setname(self):
        milky_way = self.env.ref("test_http.milky_way")

        milky_way.invalidate_recordset()
        res = self.url_open(
            f"/test_http/{milky_way.id}/setname?readonly=0",
            {
                "name": "Wilky May",
                "csrf_token": odoo.http.Request.csrf_token(self),
            },
        )
        res.raise_for_status()

        milky_way.invalidate_recordset()
        self.assertEqual(milky_way.name, "Wilky May")

    def test_models5_stargate_setname_readonly(self):
        milky_way = self.env.ref("test_http.milky_way")

        self.assertEqual(milky_way.name, "Milky Way")

        # No cursor ERROR log expected: pipeline mode defers SQL execution,
        # so ReadOnlySqlTransaction is raised during pipeline exit, not
        # during cursor.execute() where the ERROR would normally be logged.
        with self.assertLogs("odoo.http.request_class", "WARNING") as capture_http:
            res = self.url_open(
                f"/test_http/{milky_way.id}/setname?readonly=1",
                {
                    "name": "Wilky May",
                    "csrf_token": odoo.http.Request.csrf_token(self),
                },
            )
            res.raise_for_status()

        milky_way.invalidate_recordset()
        self.assertEqual(milky_way.name, "Wilky May")
        self.assertEqual(
            capture_http.output,
            [
                Like(
                    "...cannot execute UPDATE in a read-only transaction, retrying with a read/write cursor..."
                ),
            ],
        )

    def test_models5_max_upload_too_large(self):
        res = self.url_open(
            "/test_http/1/setname", {"name": "too much data" * 1000}
        )  # 1.3kB
        self.assertEqual(res.status_code, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)

    def test_models6_rpc_path_poisoning(self):
        with self.assertLogs("werkzeug", logging.INFO) as capture:
            with mute_logger("odoo.addons.rpc.controllers.xmlrpc"):
                self.xmlrpc_object.execute_kw(
                    get_db_name(),
                    self.jackoneill.id,
                    "jackoneill",
                    "res.users",
                    "read",
                    [self.jackoneill.id, ["login"]],
                )
            res = self.url_open("/test_http/wsgi_environ")
            res.raise_for_status()

        self.assertEqual(
            capture.output,
            [
                Like('..."POST /xmlrpc/2/object#res.users.read HTTP/...'),
                Like('..."GET /test_http/wsgi_environ HTTP/...'),
            ],
            "there must be two requests, the first with a fragment, the second without",
        )

        environ = {
            "PATH_INFO": "/test_http/wsgi_environ",
            "QUERY_STRING": "",
            "REQUEST_URI": "/test_http/wsgi_environ",
            "RAW_URI": "/test_http/wsgi_environ",
        }
        self.assertEqual(
            submap(res.json(), environ.keys()),
            environ,
            "the fragment must not leak in the next request",
        )
        self.assertNotIn(
            "#res.users/read",
            res.text,
            "the fragment must not leak in the next request",
        )
