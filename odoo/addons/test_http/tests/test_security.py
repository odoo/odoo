import json

from .test_common import TestHttpBase
from odoo.addons.test_http.controllers import CT_JSON


class TestHttpSecurity(TestHttpBase):
    def test_httprequest_attrs(self):
        res = self.db_url_open("/test_http/httprequest_attrs")
        result = json.loads(res.content)
        self.assertNotIn("user_agent_class", result)
        self.assertNotIn("parameter_storage_class", result)

    def test_httprequest_environ(self):
        res = self.db_url_open("/test_http/httprequest_environ")
        result = json.loads(res.content)
        self.assertNotIn("wsgi.input", result)
        self.assertNotIn("werkzeug.socket", result)
        self.assertNotIn("socket", result)

    def test_nul_byte_in_path_is_refused_as_malformed_not_500(self):
        for path in (
            "/test_http/greeting%00",
            "/web/static/src/img/x%00.png",
            "/%00",
        ):
            with self.subTest(path=path):
                res = self.db_url_open(path)
                self.assertEqual(res.status_code, 400, res.text[:200])

    def test_nul_byte_in_query_string_is_harmless(self):
        res = self.db_url_open("/test_http/echo-http-get?x=%00")
        self.assertEqual(res.status_code, 200)

    def test_malformed_requests_never_5xx(self):
        img = "/test_http/static/src/img/gizeh.png"
        cases = [
            ("encoded dot-dot", "GET", "/test_http/greeting%2e%2e%2f", {}, None),
            ("invalid utf-8 path", "GET", "/test_http/greeting%ff", {}, None),
            ("overlong utf-8 path", "GET", "/test_http/greeting%c0%af", {}, None),
            ("very long path", "GET", "/test_http/" + "a" * 4000, {}, None),
            ("many segments", "GET", "/" + "a/" * 900, {}, None),
            ("CRLF in path", "GET", "/test_http/g%0d%0aX-Injected:%201", {}, None),
            ("NUL as query key", "GET", "/test_http/greeting?%00=1", {}, None),
            ("invalid utf-8 query", "GET", "/test_http/greeting?a=%ff", {}, None),
            ("static dir, no file", "GET", "/test_http/static/src", {}, None),
            (
                "absurd Accept-Language",
                "GET",
                "/test_http/greeting",
                {"Accept-Language": "x" * 3000},
                None,
            ),
            (
                "malformed Accept-Language",
                "GET",
                "/test_http/greeting",
                {"Accept-Language": "!!!;q=abc, ,,"},
                None,
            ),
            (
                "Accept-Language modifier",
                "GET",
                "/test_http/greeting",
                {"Accept-Language": "it-IT@euro"},
                None,
            ),
            ("bogus Range", "GET", img, {"Range": "bytes=abc-xyz"}, None),
            (
                "unsatisfiable Range",
                "GET",
                img,
                {"Range": "bytes=99999999999-99999999999"},
                None,
            ),
            (
                "bogus If-Modified-Since",
                "GET",
                img,
                {"If-Modified-Since": "not a date"},
                None,
            ),
            (
                "garbage X-Forwarded-For",
                "GET",
                "/test_http/greeting",
                {"X-Forwarded-For": "not-an-ip, ,,"},
                None,
            ),
            (
                "oversized session cookie",
                "GET",
                "/test_http/greeting",
                {"Cookie": "session_id=" + "a" * 5000},
                None,
            ),
            (
                "deeply nested json",
                "POST",
                "/test_http/echo-json",
                CT_JSON,
                '{"params":' + "[" * 400 + "]" * 400 + "}",
            ),
            (
                "huge json int",
                "POST",
                "/test_http/echo-json",
                CT_JSON,
                '{"params":{"n":' + "9" * 400 + "}}",
            ),
            (
                "json params is a list",
                "POST",
                "/test_http/echo-json",
                CT_JSON,
                '{"params":[1,2]}',
            ),
            ("json body is null", "POST", "/test_http/echo-json", CT_JSON, "null"),
            (
                "truncated multipart",
                "POST",
                "/test_http/echo-http-post",
                {"Content-Type": "multipart/form-data; boundary=XX"},
                "--XX\r\nContent-Disposition: form-data; name=",
            ),
            ("typed: empty int", "GET", "/test_http/typed-echo?n=", {}, None),
            ("typed: float overflow", "GET", "/test_http/typed-echo?n=1e999", {}, None),
            ("typed: missing required", "GET", "/test_http/typed-echo", {}, None),
        ]
        for label, method, path, headers, data in cases:
            with self.subTest(case=label):
                res = self.db_url_open(path, data=data, headers=headers, method=method)
                self.assertLess(
                    res.status_code,
                    500,
                    f"{label}: {method} {path[:60]} produced {res.status_code}",
                )
