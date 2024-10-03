# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import Request
from odoo.tests import tagged
from odoo.tests.common import new_test_user
from odoo.tools import mute_logger
from odoo.addons.test_http.controllers import CT_JSON

from .test_common import TestHttpBase


@tagged('post_install', '-at_install')
class TestHttpEchoReplyHttpNoDB(TestHttpBase):
    def test_echohttp0_get_qs_nodb(self):
        res = self.nodb_url_open('/test_http/echo-http-get?race=Asgard')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard'}")

    def test_echohttp1_get_form_nodb(self):
        res = self.nodb_url_open('/test_http/echo-http-get', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 405)

    def test_echohttp2_post_qs_nodb(self):
        res = self.nodb_url_open('/test_http/echo-http-post?race=Asgard')
        self.assertEqual(res.status_code, 405)

    def test_echohttp3_post_qs_form_nodb(self):
        res = self.nodb_url_open('/test_http/echo-http-post?race=Asgard', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard', 'commander': 'Thor'}")

    @mute_logger('odoo.http')
    def test_echohttp4_post_json_nodb(self):
        payload = json.dumps({'commander': 'Thor'})
        res = self.nodb_url_open('/test_http/echo-http-post', data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{}')


    def test_echohttp5_post_csrf(self):
        res = self.nodb_url_open('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 303)
        self.assertURLEqual(res.headers.get('Location'), '/web/database/selector')

    def test_echohttp6_json_over_http(self):
        payload = json.dumps({'commander': 'Thor'})
        res = self.nodb_url_open('/test_http/echo-json-over-http', data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, payload)
        mimetype = res.headers['Content-Type'].partition(';')[0]
        self.assertEqual(mimetype, 'application/json')


@tagged('post_install', '-at_install')
class TestHttpEchoReplyJsonNoDB(TestHttpBase):
    def test_echojson0_qs_json_nodb(self):
        payload = json.dumps({
            'jsonrpc': '2.0',
            'id': 1234,
            'params': {
                'commander': 'Thor',
            },
        })
        res = self.nodb_url_open("/test_http/echo-json?race=Asgard", data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{"jsonrpc": "2.0", "id": 1234, "result": {"commander": "Thor"}}')

    def test_echojson1_http_get_nodb(self):
        res = self.nodb_url_open('/test_http/echo-json')  # GET
        self.assertEqual(res.status_code, 405)

    @mute_logger('odoo.http')
    def test_echojson2_http_post_nodb(self):
        res = self.nodb_url_open('/test_http/echo-json', data={'race': 'Asgard'})  # POST
        self.assertIn("Bad Request", res.text)

    def test_echojson3_bad_json(self):
        payload = 'some non json garbage'
        res = self.nodb_url_open("/test_http/echo-json", data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 400, res.text)
        self.assertEqual(res.text, "Invalid JSON data")

    def test_echojson4_bad_jsonrpc(self):
        payload = '"I am a json string"'
        res = self.nodb_url_open("/test_http/echo-json", data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 400, res.text)
        self.assertEqual(res.text, "Invalid JSON-RPC data")


@tagged('post_install', '-at_install')
class TestHttpEchoReplyHttpWithDB(TestHttpBase):
    def setUp(self):
        super().setUp()
        self.jackoneill = new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})
        self.authenticate('jackoneill', 'jackoneill')

    def test_echohttp0_get_qs_db(self):
        res = self.db_url_open('/test_http/echo-http-get?race=Asgard')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard'}")

    def test_echohttp1_get_form_db(self):
        res = self.db_url_open('/test_http/echo-http-get', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 405)

    def test_echohttp2_post_qs_db(self):
        res = self.db_url_open('/test_http/echo-http-post?race=Asgard')
        self.assertEqual(res.status_code, 405)

    def test_echohttp3_post_qs_form_db(self):
        res = self.db_url_open('/test_http/echo-http-post?race=Asgard', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard', 'commander': 'Thor'}")

    @mute_logger('odoo.http')
    def test_echohttp4_post_json_db(self):
        payload = json.dumps({'commander': 'Thor'})
        res = self.db_url_open('/test_http/echo-http-post', data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{}')

    @mute_logger('odoo.http')
    def test_echohttp5_post_no_csrf(self):
        res = self.db_url_open('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Session expired (invalid CSRF token)", res.text)

    @mute_logger('odoo.http')
    def test_echohttp6_post_bad_csrf(self):
        res = self.db_url_open('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor', 'csrf_token': 'bad token'})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Session expired (invalid CSRF token)", res.text)

    @mute_logger('odoo.http')
    def test_echohttp7_post_good_csrf(self):
        res = self.db_url_open('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor', 'csrf_token': Request.csrf_token(self)})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard', 'commander': 'Thor'}")


@tagged('post_install', '-at_install')
class TestHttpEchoReplyJsonWithDB(TestHttpBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.jackoneill = new_test_user(cls.env, 'jackoneill', context={'lang': 'en_US'})

    def setUp(self):
        super().setUp()
        self.authenticate('jackoneill', 'jackoneill')

    def test_echojson0_qs_json_db(self):
        payload = json.dumps({
            'jsonrpc': '2.0',
            'id': 1234,
            'params': {
                'commander': 'Thor',
            },
        })
        res = self.db_url_open('/test_http/echo-json?race=Asgard', data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{"jsonrpc": "2.0", "id": 1234, "result": {"commander": "Thor"}}')

    def test_echojson1_http_get_db(self):
        res = self.db_url_open('/test_http/echo-json')  # GET
        self.assertEqual(res.status_code, 405)

    @mute_logger('odoo.http')
    def test_echojson2_http_post_db(self):
        res = self.db_url_open('/test_http/echo-json', data={'race': 'Asgard'})  # POST
        self.assertIn("Bad Request", res.text)

    def test_echojson3_context_db(self):
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 0,
            "params": {
                "context": {
                    "name": "Thor"
                },
                "race": "Asgard",
            },
        })
        res = self.db_url_open("/test_http/echo-json-context", data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, '{"jsonrpc": "2.0", "id": 0, "result": '
            f'{{"lang": "en_US", "tz": false, "uid": {self.jackoneill.id}}}'
            '}')

    def test_echojson3_bad_json(self):
        payload = 'some non json garbage'
        res = self.db_url_open("/test_http/echo-json", data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 400, res.text)
        self.assertEqual(res.text, "Invalid JSON data")

    def test_echojson4_bad_jsonrpc(self):
        payload = '"I am a json string"'
        res = self.db_url_open("/test_http/echo-json", data=payload, headers=CT_JSON)
        self.assertEqual(res.status_code, 400, res.text)
        self.assertEqual(res.text, "Invalid JSON-RPC data")
