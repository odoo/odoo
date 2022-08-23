# Part of Odoo. See LICENSE file for full copyright and licensing details.
from urllib.parse import urlparse

from odoo.http import Request
from odoo.tests import tagged
from odoo.tests.common import new_test_user, WsgiCase, HttpCase
from odoo.tools import mute_logger
from .test_common import HttpTestMixin, nodb


class EchoReplyHttpNoDBMixin(HttpTestMixin):
    @nodb()
    def test_echohttp0_get_qs_nodb(self):
        res = self.opener.get('/test_http/echo-http-get?race=Asgard')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard'}")

    @nodb()
    def test_echohttp1_get_form_nodb(self):
        res = self.opener.post('/test_http/echo-http-get', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 405)

    @nodb()
    def test_echohttp2_post_qs_nodb(self):
        res = self.opener.get('/test_http/echo-http-post?race=Asgard')
        self.assertEqual(res.status_code, 405)

    @nodb()
    def test_echohttp3_post_qs_form_nodb(self):
        res = self.opener.post('/test_http/echo-http-post?race=Asgard', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard', 'commander': 'Thor'}")

    @mute_logger('odoo.http')
    def test_echohttp4_post_json_nodb(self):
        res = self.opener.post('/test_http/echo-http-post', json={'commander': 'Thor'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{}')

    @nodb()
    def test_echohttp5_post_csrf(self):
        res = self.opener.post(
            '/test_http/echo-http-csrf?race=Asgard',
            data={'commander': 'Thor'},
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 303)
        self.assertEqual(
            urlparse(res.headers.get('Location', '')).path,
            '/web/database/selector'
        )

    @nodb()
    def test_echohttp6_json_over_http(self):
        res = self.opener.post('/test_http/echo-json-over-http', json={'commander': 'Thor'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{"commander": "Thor"}')
        mimetype = res.headers['Content-Type'].partition(';')[0]
        self.assertEqual(mimetype, 'application/json')

class EchoReplyJsonNoDbMixin(HttpTestMixin):
    @nodb()
    def test_echojson0_qs_json_nodb(self):
        payload = {
            'jsonrpc': '2.0',
            'id': 1234,
            'params': {
                'commander': 'Thor',
            },
        }
        res = self.opener.post("/test_http/echo-json?race=Asgard", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{"jsonrpc": "2.0", "id": 1234, "result": {"commander": "Thor"}}')

    @nodb()
    def test_echojson1_http_get_nodb(self):
        res = self.opener.get('/test_http/echo-json')
        self.assertEqual(res.status_code, 405)

    @nodb()
    @mute_logger('odoo.http')
    def test_echojson2_http_post_nodb(self):
        res = self.opener.post('/test_http/echo-json', data={'race': 'Asgard'})
        self.assertIn("Bad Request", res.text)

class EchoReplyHttpWithDBMixin(HttpTestMixin):
    def setUp(self):
        super().setUp()
        self.jackoneill = new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})
        self.authenticate('jackoneill', 'jackoneill')

    def test_echohttp0_get_qs_db(self):
        res = self.opener.get('/test_http/echo-http-get?race=Asgard')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard'}")

    def test_echohttp1_get_form_db(self):
        res = self.opener.post('/test_http/echo-http-get', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 405)

    def test_echohttp2_post_qs_db(self):
        res = self.opener.get('/test_http/echo-http-post?race=Asgard')
        self.assertEqual(res.status_code, 405)

    def test_echohttp3_post_qs_form_db(self):
        res = self.opener.post('/test_http/echo-http-post?race=Asgard', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard', 'commander': 'Thor'}")

    @mute_logger('odoo.http')
    def test_echohttp4_post_json_db(self):
        res = self.opener.post('/test_http/echo-http-post', json={'commander': 'Thor'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{}')

    @mute_logger('odoo.http')
    def test_echohttp5_post_no_csrf(self):
        res = self.opener.post('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Session expired (invalid CSRF token)", res.text)

    @mute_logger('odoo.http')
    def test_echohttp6_post_bad_csrf(self):
        res = self.opener.post('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor', 'csrf_token': 'bad token'})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Session expired (invalid CSRF token)", res.text)

    @mute_logger('odoo.http')
    def test_echohttp7_post_good_csrf(self):
        res = self.opener.post('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor', 'csrf_token': Request.csrf_token(self)})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard', 'commander': 'Thor'}")

class EchoReplyJsonWithDBMixin(HttpTestMixin):
    def setUp(self):
        super().setUp()
        self.jackoneill = new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})
        self.authenticate('jackoneill', 'jackoneill')

    def test_echojson0_qs_json_db(self):
        res = self.opener.post('/test_http/echo-json?race=Asgard', json={
            'jsonrpc': '2.0',
            'id': 1234,
            'params': {
                'commander': 'Thor',
            },
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{"jsonrpc": "2.0", "id": 1234, "result": {"commander": "Thor"}}')

    def test_echojson1_http_get_db(self):
        res = self.opener.get('/test_http/echo-json')
        self.assertEqual(res.status_code, 405)

    @mute_logger('odoo.http')
    def test_echojson2_http_post_db(self):
        res = self.opener.post('/test_http/echo-json', data={'race': 'Asgard'})
        self.assertIn("Bad Request", res.text)

    def test_echojson3_context_db(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "params": {
                "context": {
                    "name": "Thor"
                },
                "race": "Asgard",
            },
        }
        res = self.opener.post("/test_http/echo-json-context", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{"jsonrpc": "2.0", "id": 0, "result": {"name": "Thor"}}')

class TestWsgiEchoReplyHttpNoDb(EchoReplyHttpNoDBMixin, WsgiCase):
    pass

@tagged('post_install', '-at_install')
class TestHttpEchoReplyHttpNoDB(EchoReplyHttpNoDBMixin, HttpCase):
    pass

class TestWsgiEchoReplyJsonNoDB(EchoReplyJsonNoDbMixin, WsgiCase):
    pass

@tagged('post_install', '-at_install')
class TestHttpEchoReplyJsonNoDB(EchoReplyJsonNoDbMixin, HttpCase):
    pass

class TestWsgiEchoReplyHttpWithDB(EchoReplyHttpWithDBMixin, WsgiCase):
    ...

@tagged('post_install', '-at_install')
class TestHttpEchoReplyHttpWithDB(EchoReplyHttpWithDBMixin, HttpCase):
    pass

class TestWsgiEchoReplyJsonWithDB(EchoReplyJsonWithDBMixin, WsgiCase):
    pass

@tagged('post_install', '-at_install')
class TestHttpEchoReplyJsonWithDB(EchoReplyJsonWithDBMixin, HttpCase):
    pass
