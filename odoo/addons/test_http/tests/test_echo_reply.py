# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import time
from http import HTTPStatus

import requests.exceptions

from odoo.http.session import SESSION_ROTATION_INTERVAL
from odoo.tests import Like, new_test_user, tagged
from odoo.tools import mute_logger
from odoo.tools.misc import submap

from .test_common import TestHttpBase
from odoo.addons.test_http.controllers import CT_JSON


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
        self.assertEqual(res.text, Like("""
            ...Request inferred type is compatible with...http...but...
            /test_http/echo-json...is type=...json...
        """))
        self.assertEqual(res.status_code, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        self.assertEqual(res.headers.get('Accept'), "application/json, application/json-rpc")

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

    def test_echojson5_null(self):
        payload = json.dumps({
            'jsonrpc': '2.0',
            'id': 1234,
            'params': {},
        })
        res = self.nodb_url_open("/test_http/echo-json-null", data=payload, headers=CT_JSON)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers['Content-Type'], 'application/json; charset=utf-8')
        self.assertEqual(res.text, r'{"jsonrpc": "2.0", "id": 1234, "result": null}', "result must not be absent")


@tagged('post_install', '-at_install')
class TestHttpEchoReplyHttpWithDB(TestHttpBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.jackoneill = new_test_user(cls.env, 'jackoneill', context={'lang': 'en_US'})

    def setUp(self):
        super().setUp()
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
        res = self.db_url_open('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor', 'csrf_token': self.csrf_token()})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard', 'commander': 'Thor'}")

    @mute_logger('odoo.http')
    def test_echohttp8_post_good_csrf_with_session_rotation(self):
        # Compute a csrf token in advance,
        # to mimic a form opened in another browser tab with the CSRF token already computed
        csrf_token = self.csrf_token()
        sid_before_rotation = self.opener.cookies['session_id']

        # Force a rotation by changing the create date of the session
        self.update_session(create_time=time.time() - SESSION_ROTATION_INTERVAL)

        # Trigger session rotation by calling another endpoint
        res = self.db_url_open('/test_http/echo-http-get')
        self.assertNotEqual(
            sid_before_rotation,
            self.opener.cookies['session_id'],
            "The session must rotate for this test to make sense",
        )

        # Do the post with the CSRF token computed in advance
        res = self.db_url_open('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor', 'csrf_token': csrf_token})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard', 'commander': 'Thor'}")

    def test_echohttp9_post_chunked(self):
        self.env['ir.config_parameter'].sudo().set_int('web.max_file_upload_size', 10)

        with self.subTest(name="short body"):
            short_body = iter('""')
            res = self.db_url_open('/test_http/echo-json-over-http', data=short_body, headers=CT_JSON)
            req = res.request
            res.raise_for_status()
            self.assertEqual(req.headers.get('Transfer-Encoding'), 'chunked')
            self.assertEqual(res.text, '""')
            self.assertFalse(list(short_body), "the body should had been sent fully")
            self.assertEqual(res.status_code, 200)

        with self.subTest(name="long body"):
            long_body = iter('"this text is too long"')
            try:
                res = self.db_url_open('/test_http/echo-json-over-http', data=long_body, headers=CT_JSON)
            except requests.exceptions.ConnectionError:
                pass
            else:
                self.assertEqual(res.status_code, 400)

            # It depends on the OS buffers and thus isn't reliable.
            # We could implement is a deterministic way but we would
            # need to send much more data and we don't want that either.
            # self.assertTrue(list(long_body), "the body shouldn't had been sent fully")


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
        self.assertEqual(res.text, Like("""
            ...Request inferred type is compatible with...http...but...
            /test_http/echo-json...is type=...json...
        """))
        self.assertEqual(res.status_code, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        self.assertEqual(res.headers.get('Accept'), "application/json, application/json-rpc")

    def test_echojson3_context_db(self):
        res = self.make_jsonrpc_request(
            '/test_http/echo-json-context',
            params={'context': {'name': 'Thor'}},
        )
        expected = {
            'lang': 'en_US',
            'tz': False,
            'uid': self.jackoneill.id,
        }
        self.assertEqual(submap(res, expected), expected)

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
