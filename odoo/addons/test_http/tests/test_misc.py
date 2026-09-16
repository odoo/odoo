import json
from io import BytesIO, StringIO
from socket import gethostbyname
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from werkzeug.datastructures import MultiDict
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

import odoo
from odoo import http
from odoo.http import prepare_content_disposition_header, rewind_uploaded_files, root
from odoo.tests import tagged
from odoo.tests.common import HOST, BaseCase, get_db_name, new_test_user
from odoo.tools import config, file_path, mute_logger

from .test_common import TestHttpBase
from odoo.addons import test_http
from odoo.addons.test_http.controllers import CT_JSON
from odoo.addons.test_http.utils import TEST_IP


@tagged("post_install", "-at_install")
class TestHttpMisc(TestHttpBase):
    def test_misc0_redirect(self):
        res = self.nodb_url_open("/test_http//greeting")
        self.assertEqual(res.status_code, 404)

    def test_misc1_reverse_proxy(self):
        client_ip = "127.0.0.16"
        reverseproxy_ip = gethostbyname(HOST)
        host = "mycompany.odoo.com"

        headers = {
            "Host": "",
            "X-Forwarded-For": client_ip,
            "X-Forwarded-Host": host,
            "X-Forwarded-Proto": "https",
        }

        with patch.object(config, "options", {**config.options, "proxy_mode": False}):
            res = self.nodb_url_open("/test_http/wsgi_environ", headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["REMOTE_ADDR"], reverseproxy_ip)
            self.assertEqual(res.json()["HTTP_HOST"], "")

        with patch.object(config, "options", {**config.options, "proxy_mode": True}):
            res = self.nodb_url_open("/test_http/wsgi_environ", headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["REMOTE_ADDR"], client_ip)
            self.assertEqual(res.json()["HTTP_HOST"], host)

    def test_misc2_local_redirect(self):
        def local_redirect(path):
            fake_req = odoo.tools.misc.DotDict(db=False)
            return odoo.http.Request.redirect(fake_req, path, local=True).headers[
                "Location"
            ]

        self.assertEqual(
            local_redirect("https://www.example.com/hello?a=b"), "/hello?a=b"
        )
        self.assertEqual(local_redirect("/hello?a=b"), "/hello?a=b")
        self.assertEqual(local_redirect("hello?a=b"), "/hello?a=b")
        self.assertEqual(
            local_redirect("www.example.com/hello?a=b"),
            "/www.example.com/hello?a=b",
        )
        self.assertEqual(
            local_redirect("https://www.example.comhttps://www.example2.com/hello?a=b"),
            "/www.example2.com/hello?a=b",
        )
        self.assertEqual(
            local_redirect("https://https://www.example.com/hello?a=b"),
            "/www.example.com/hello?a=b",
        )

    def test_misc2_redirect_query_fragment_order(self):
        captured = {}

        def fake_redirect(location, code=303, local=True):
            captured["location"] = location
            return location

        def location_from_redirect_query(path, query):
            fake_req = MagicMock()
            fake_req.db = False
            fake_req.redirect = fake_redirect
            odoo.http.Request.redirect_query(fake_req, path, query=query, local=True)
            return captured["location"]

        self.assertEqual(
            location_from_redirect_query("/foo", {"a": "b"}),
            "/foo?a=b",
        )
        self.assertEqual(
            location_from_redirect_query("/foo?x=1", {"a": "b"}),
            "/foo?x=1&a=b",
        )
        self.assertEqual(
            location_from_redirect_query("/foo#bar", {"a": "b"}),
            "/foo?a=b#bar",
        )
        self.assertEqual(
            location_from_redirect_query("/foo?x=1#bar", {"a": "b"}),
            "/foo?x=1&a=b#bar",
        )

    def test_misc3_is_static_file(self):
        uri = "test_http/static/src/img/gizeh.png"
        path = file_path(uri)

        self.assertEqual(root.get_static_file_path(f"/{uri}"), path, "Valid file")
        self.assertEqual(
            root.get_static_file_path(f"odoo.com/{uri}", host="odoo.com"),
            path,
            "Valid file with valid host",
        )
        self.assertEqual(
            root.get_static_file_path(f"http://odoo.com/{uri}", host="odoo.com"),
            path,
            "Valid file with valid host",
        )
        self.assertEqual(
            root.get_static_file_path(f"http://ODOO.com/{uri}", host="odoo.com"),
            path,
            "Valid file with case-mismatched host in URL",
        )
        self.assertEqual(
            root.get_static_file_path(f"odoo.com/{uri}", host="Odoo.COM"),
            path,
            "Valid file with case-mismatched expected host",
        )

        self.assertIsNone(
            root.get_static_file_path("/test_http/i-dont-exist"),
            "File doesn't exist",
        )
        self.assertIsNone(
            root.get_static_file_path("/test_http/__manifest__.py"),
            "File is not static",
        )
        self.assertIsNone(
            root.get_static_file_path(f"odoo.com/{uri}"), "No host allowed"
        )
        self.assertIsNone(
            root.get_static_file_path(f"http://odoo.com/{uri}"), "No host allowed"
        )

    def test_misc4_rpc_qweb(self):
        jack = new_test_user(self.env, "jackoneill", context={"lang": "en_US"})
        milky_way = self.env.ref("test_http.milky_way")

        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "call",
                "id": None,
                "params": {
                    "service": "object",
                    "method": "execute",
                    "args": [
                        get_db_name(),
                        jack.id,
                        "jackoneill",
                        "test_http.galaxy",
                        "render",
                        milky_way.id,
                    ],
                },
            }
        )

        for method in (self.db_url_open, self.nodb_url_open):
            with self.subTest(method=method.__name__):
                with mute_logger("odoo.addons.rpc.controllers.jsonrpc"):
                    res = method("/jsonrpc", data=payload, headers=CT_JSON)
                res.raise_for_status()

                res_rpc = res.json()
                self.assertNotIn(
                    "error",
                    res_rpc.keys(),
                    res_rpc.get("error", {}).get("data", {}).get("message"),
                )
                self.assertIn(
                    milky_way.name,
                    res_rpc["result"],
                    "QWeb template was correctly rendered",
                )

    def test_misc5_geoip(self):
        res = self.nodb_url_open("/test_http/geoip")
        res.raise_for_status()
        self.assertEqual(
            res.json(),
            {
                "city": None,
                "country_code": None,
                "country_name": None,
                "latitude": None,
                "longitude": None,
                "region": None,
                "time_zone": None,
            },
        )

        headers = {
            "Host": "",
            "X-Forwarded-For": TEST_IP,
            "X-Forwarded-Host": "odoo.com",
            "X-Forwarded-Proto": "https",
        }
        with odoo.tools.config.patch(proxy_mode=True):
            res = self.nodb_url_open("/test_http/geoip", headers=headers)
            res.raise_for_status()
            self.assertEqual(
                res.json(),
                {
                    "city": None,
                    "country_code": "FR",
                    "country_name": "France",
                    "latitude": 48.8582,
                    "longitude": 2.3387,
                    "region": None,
                    "time_zone": "Europe/Paris",
                },
            )

    def test_misc6_upload_file_retry(self):
        file = StringIO("Hello world!")
        with patch.object(test_http.controllers, "should_fail", True):
            res = self.url_open("/test_http/upload_file", files={"ufile": file})
            res.raise_for_status()
            self.assertEqual(res.text, file.getvalue())

    def test_misc7_robotstxt(self):
        self.nodb_url_open("/robots.txt").raise_for_status()

    def test_misc8_concurrency_error(self):
        with (
            self.assertLogs("odoo.service.model") as log_catcher,
            patch.object(test_http.controllers, "should_fail", True),
        ):
            self.url_open("/test_http/concurrency_error").raise_for_status()
        self.assertIn("A dummy concurrency error occurred", log_catcher.output[0])

    def test_misc9_webversion(self):
        res = self.nodb_url_open("/web/version")
        res.raise_for_status()
        self.assertEqual(
            res.headers.get("Content-Type"), "application/json; charset=utf-8"
        )
        self.assertEqual(set(res.json()), {"version", "version_info"})

    def test_misc10_cookie_default_expires_is_utc(self):
        import datetime as dt

        from odoo.http._cookies import _prepare_set_cookie_args

        expires, _max_age, _secure, _samesite = _prepare_set_cookie_args(
            -1, None, "required", None, None
        )
        self.assertEqual(expires.utcoffset(), dt.timedelta(0))
        expected = dt.datetime.now(tz=dt.UTC) + dt.timedelta(days=365)
        self.assertLess(abs((expires - expected).total_seconds()), 60)


@tagged("post_install", "-at_install")
class TestHttpCors(TestHttpBase):
    def test_cors0_http_default(self):
        res_opt = self.url_open(
            f"{self.base_url()}/test_http/cors_http_default",
            timeout=10,
            method="OPTIONS",
        )
        self.assertIn(res_opt.status_code, (200, 204))
        self.assertEqual(res_opt.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(
            res_opt.headers.get("Access-Control-Allow-Methods"), "GET, POST"
        )
        self.assertEqual(res_opt.headers.get("Access-Control-Max-Age"), "86400")
        self.assertEqual(
            res_opt.headers.get("Access-Control-Allow-Headers"),
            "Origin, X-Requested-With, Content-Type, Accept, Authorization, Range",
        )

        res_get = self.url_open("/test_http/cors_http_default")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(
            res_get.headers.get("Access-Control-Allow-Methods"), "GET, POST"
        )

    def test_cors1_http_methods(self):
        res_opt = self.url_open(
            f"{self.base_url()}/test_http/cors_http_methods",
            timeout=10,
            method="OPTIONS",
        )
        self.assertIn(res_opt.status_code, (200, 204))
        self.assertEqual(res_opt.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(
            res_opt.headers.get("Access-Control-Allow-Methods"), "GET, PUT"
        )
        self.assertEqual(res_opt.headers.get("Access-Control-Max-Age"), "86400")
        self.assertEqual(
            res_opt.headers.get("Access-Control-Allow-Headers"),
            "Origin, X-Requested-With, Content-Type, Accept, Authorization, Range",
        )

        res_post = self.url_open("/test_http/cors_http_methods")
        self.assertEqual(res_post.status_code, 200)
        self.assertEqual(res_post.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(
            res_post.headers.get("Access-Control-Allow-Methods"), "GET, PUT"
        )

    def test_cors1_preflight_reflects_requested_headers(self):
        res_opt = self.url_open(
            f"{self.base_url()}/test_http/cors_http_default",
            timeout=10,
            method="OPTIONS",
            headers={"Access-Control-Request-Headers": "x-custom-header, range"},
        )
        self.assertIn(res_opt.status_code, (200, 204))
        self.assertEqual(
            res_opt.headers.get("Access-Control-Allow-Headers"),
            "x-custom-header, range",
        )

    def test_cors2_json(self):
        res_opt = self.url_open(
            f"{self.base_url()}/test_http/cors_json",
            timeout=10,
            method="OPTIONS",
        )
        self.assertIn(res_opt.status_code, (200, 204), res_opt.text)
        self.assertEqual(res_opt.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(res_opt.headers.get("Access-Control-Allow-Methods"), "POST")
        self.assertEqual(res_opt.headers.get("Access-Control-Max-Age"), "86400")
        self.assertEqual(
            res_opt.headers.get("Access-Control-Allow-Headers"),
            "Origin, X-Requested-With, Content-Type, Accept, Authorization, Range",
        )

        res_post = self.url_open(
            "/test_http/cors_json",
            data=json.dumps({"params": {}}),
            headers=CT_JSON,
        )
        self.assertEqual(res_post.status_code, 200)
        self.assertEqual(res_post.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(res_post.headers.get("Access-Control-Allow-Methods"), "POST")

    def test_cors3_preflight_declares_what_it_varies_on(self):
        res_opt = self.url_open(
            f"{self.base_url()}/test_http/cors_http_default",
            timeout=10,
            method="OPTIONS",
            headers={"Access-Control-Request-Headers": "x-custom-header"},
        )
        self.assertIn(
            "access-control-request-headers",
            res_opt.headers.get("Vary", "").lower(),
        )

    @mute_logger("odoo.http")
    def test_cors4_error_response_keeps_cors_headers(self):
        res = self.url_open("/test_http/cors_http_error")
        self.assertEqual(res.status_code, 422)
        self.assertEqual(
            res.headers.get("Access-Control-Allow-Origin"),
            "*",
            "the error response lost the CORS headers set by pre_dispatch",
        )
        self.assertEqual(res.headers.get("Access-Control-Allow-Methods"), "GET, POST")


@tagged("post_install", "-at_install")
class TestHttpMethodsAllowList(TestHttpBase):
    def test_methods0_options_does_not_bypass_a_post_only_route(self):
        res = self.db_url_open("/test_http/echo-http-csrf?injected=1", method="OPTIONS")
        self.assertEqual(res.status_code, 204, res.text)
        self.assertNotIn("injected", res.text, "the endpoint must not have run")
        self.assertEqual(res.headers.get("Allow"), "POST, OPTIONS")

    def test_methods2_options_answer_is_uniform_across_routes(self):
        allow_listed = self.db_url_open("/test_http/echo-http-csrf", method="OPTIONS")
        unrestricted = self.db_url_open("/test_http/greeting", method="OPTIONS")
        self.assertEqual(allow_listed.status_code, 204)
        self.assertEqual(unrestricted.status_code, 204)
        self.assertIn("OPTIONS", allow_listed.headers.get("Allow", ""))
        self.assertIn("OPTIONS", unrestricted.headers.get("Allow", ""))

    def test_methods3_trace_is_rejected_before_dispatch(self):
        res = self.db_url_open("/test_http/echo-http-csrf", method="TRACE")
        self.assertEqual(res.status_code, 405, res.text)
        res = self.db_url_open("/test_http/greeting", method="TRACE")
        self.assertEqual(res.status_code, 405, res.text)
        self.assertNotIn("Tek", res.text, "the endpoint must not have run")

    def test_methods1_preflight_still_reaches_a_cors_route(self):
        res = self.url_open(
            f"{self.base_url()}/test_http/cors_http_methods",
            timeout=10,
            method="OPTIONS",
        )
        self.assertIn(res.status_code, (200, 204))


@tagged("post_install", "-at_install")
class TestHttpEnsureDb(TestHttpBase):
    def setUp(self):
        super().setUp()
        self.dbs_served = ["db0", "db1"]

    def test_ensure_db0_db_selector(self):
        for url in ("/web", "/test_http/ensure_db"):
            with self.subTest(url=url):
                res = self.multidb_url_open(url)
                res.raise_for_status()
                self.assertEqual(res.status_code, 303)
                self.assertURLEqual(
                    res.headers.get("Location"), "/web/database/selector"
                )

    def test_ensure_db1_grant_db(self):
        res = self.multidb_url_open("/test_http/ensure_db?db=db0")
        res.raise_for_status()
        self.assertEqual(res.status_code, 302)
        self.assertURLEqual(res.headers.get("Location"), "/test_http/ensure_db?db=db0")
        self.assertEqual(
            odoo.http.root.session_store.get(res.cookies["session_id"]).db,
            "db0",
        )

        res = self.multidb_url_open("/test_http/ensure_db")
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "db0")

    def test_ensure_db2_use_session_db(self):
        session = self.authenticate(None, None)
        session.db = "db0"
        odoo.http.root.session_store.save(session)

        res = self.multidb_url_open("/test_http/ensure_db")
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "db0")

    def test_ensure_db3_change_db(self):
        session = self.authenticate(None, None)
        session.db = "db0"
        odoo.http.root.session_store.save(session)

        res = self.multidb_url_open("/test_http/ensure_db?db=db1")
        res.raise_for_status()
        self.assertEqual(res.status_code, 302)
        self.assertURLEqual(res.headers.get("Location"), "/test_http/ensure_db?db=db1")

        new_session = odoo.http.root.session_store.get(res.cookies["session_id"])
        self.assertNotEqual(session.sid, new_session.sid)
        self.assertEqual(new_session.db, "db1")
        self.assertEqual(new_session.uid, None)

        self.opener.cookies.set("session_id", new_session.sid, domain=HOST)
        res = self.multidb_url_open("/test_http/ensure_db")
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "db1")

    def test_ensure_db4_unicode(self):
        self.dbs_served = ["basededonnée1", "basededonnée2"]

        res = self.multidb_url_open("/test_http/ensure_db?db=basededonnée1")
        res.raise_for_status()
        self.assertEqual(res.status_code, 302)
        self.assertURLEqual(
            res.headers.get("Location"), "/test_http/ensure_db?db=basededonnée1"
        )
        self.assertEqual(
            odoo.http.root.session_store.get(res.cookies["session_id"]).db,
            "basededonnée1",
        )

        res = self.multidb_url_open("/test_http/ensure_db")
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "basededonnée1")


class TestContentDisposition(BaseCase):
    def test_content_disposition(self):
        assertions = [
            ("foo bar.xls", "foo%20bar.xls", "Space character"),
            ("foo(bar).xls", "foo%28bar%29.xls", "Parenthesis"),
            ("foo<bar>.xls", "foo%3Cbar%3E.xls", "Angle brackets"),
            ("foo[bar].xls", "foo%5Bbar%5D.xls", "Brackets"),
            ("foo{bar}.xls", "foo%7Bbar%7D.xls", "Curly brackets"),
            ("foo@bar.xls", "foo%40bar.xls", "At sign"),
            ("foo,bar.xls", "foo%2Cbar.xls", "Comma sign"),
            ("foo;bar.xls", "foo%3Bbar.xls", "Semicolon sign"),
            ("foo:bar.xls", "foo%3Abar.xls", "Colon sign"),
            ("foo\\bar.xls", "foo%5Cbar.xls", "Backslash sign"),
            ('foo"bar.xls', "foo%22bar.xls", "Double quote sign"),
            ("foo/bar.xls", "foo%2Fbar.xls", "Slash sign"),
            ("foo?bar.xls", "foo%3Fbar.xls", "Question mark"),
            ("foo=bar.xls", "foo%3Dbar.xls", "Equal sign"),
            ("foo*bar.xls", "foo%2Abar.xls", "Star sign"),
            ("foo'bar.xls", "foo%27bar.xls", "Single-quote sign"),
            ("foo%bar.xls", "foo%25bar.xls", "Percent sign"),
        ]
        for filename, pct_encoded, hint in assertions:
            self.assertEqual(
                prepare_content_disposition_header(filename),
                f"attachment; filename*=UTF-8''{pct_encoded}",
                f"{hint} should be percent encoded",
            )


class TestRewindUploadedFiles(BaseCase):
    def test_rewind_single_file(self):
        builder = EnvironBuilder(
            method="POST", data={"ufile": (BytesIO(b"Hello world!"), "a.txt")}
        )
        req = Request(builder.get_environ())
        (upload,) = req.files.getlist("ufile")
        upload.stream.read()

        rewind_uploaded_files(req, cause=RuntimeError("serialization failure"))

        self.assertEqual(upload.read(), b"Hello world!")

    def test_rewind_multifile_same_field(self):
        contents = [b"AAAAA-file-one", b"BBBBB-file-two", b"CCCCC-file-three"]
        builder = EnvironBuilder(
            method="POST",
            data={
                "attachments": [
                    (BytesIO(c), f"f{i}.txt") for i, c in enumerate(contents)
                ]
            },
        )
        req = Request(builder.get_environ())
        uploads = req.files.getlist("attachments")
        self.assertEqual(len(uploads), 3, "sanity: all three files parsed")

        for upload in uploads:
            upload.stream.read()
        self.assertEqual(
            [u.read() for u in uploads], [b"", b"", b""], "sanity: all at EOF"
        )

        rewind_uploaded_files(req, cause=RuntimeError("serialization failure"))

        self.assertEqual([u.read() for u in uploads], contents)

    def test_rewind_nonseekable_raises_chained(self):

        class _NonSeekable:
            def seekable(self):
                return False

        req = SimpleNamespace(files=MultiDict([("ufile", _NonSeekable())]))
        cause = RuntimeError("serialization failure")

        with self.assertRaises(RuntimeError) as cm:
            rewind_uploaded_files(req, cause=cause)

        self.assertIs(cm.exception.__cause__, cause)
        self.assertIn("ufile", str(cm.exception))


@tagged("post_install", "-at_install")
class TestHttpJson2Params(TestHttpBase):
    def test_json2_0_query_string_reaches_the_handler(self):
        res = self.db_url_open("/test_http/echo-json2?q=hello&n=1")
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json(), {"q": "hello", "n": "1"})

    def test_json2_1_body_wins_over_the_query_string(self):
        res = self.db_url_open(
            "/test_http/echo-json2?q=from-query",
            data=json.dumps({"q": "from-body"}),
            headers=CT_JSON,
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json(), {"q": "from-body"})


@tagged("post_install", "-at_install")
class TestHttpCorsCredentials(TestHttpBase):
    def test_cors0_resolver_allows_an_origin_on_this_host(self):
        base = self.base_url()
        res = self.url_open(
            f"{base}/test_http/cors-resolver", headers={"Origin": base}, timeout=10
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), base)
        self.assertEqual(res.headers.get("Access-Control-Allow-Credentials"), "true")
        self.assertIn("Origin", res.headers.get("Vary", ""))

    def test_cors1_resolver_refuses_a_foreign_origin(self):
        res = self.url_open(
            f"{self.base_url()}/test_http/cors-resolver",
            headers={"Origin": "https://evil.example"},
            timeout=10,
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertIsNone(res.headers.get("Access-Control-Allow-Origin"))
        self.assertIsNone(res.headers.get("Access-Control-Allow-Credentials"))
        self.assertIn("Origin", res.headers.get("Vary", ""))

    def test_cors2_wildcard_with_credentials_is_refused_at_decoration(self):
        with self.assertRaises(ValueError):

            @http.route(
                "/test_http/never",
                type="http",
                auth="none",
                cors="*",
                cors_credentials=True,
            )
            def never(self): ...
