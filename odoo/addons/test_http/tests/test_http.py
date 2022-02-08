# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import unittest
from html.parser import HTMLParser
from unittest.mock import patch
from urllib.parse import urlparse
from socket import gethostbyname

import odoo
from odoo.http import WebRequest
from odoo.tests import tagged
from odoo.tests.common import HOST, HttpCase, new_test_user
from odoo.tools import config, file_open, mute_logger
from odoo.tools.func import lazy_property
from odoo.addons.test_http.controllers import CT_JSON


# pylint: disable=W0223(abstract-method)
class HtmlTokenizer(HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tokens = []

    @classmethod
    def _attrs_to_str(cls, attrs):
        out = []
        for key, value in attrs:
            out.append(f"{key}={value!r}" if value else key)
        return " ".join(out)

    def handle_starttag(self, tag, attrs):
        self.tokens.append(f"<{tag} {self._attrs_to_str(attrs)}>")

    def handle_endtag(self, tag):
        self.tokens.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        # HTML5 <img> instead of XHTML <img/>
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        data = data.strip()
        if data:
            self.tokens.append(data)

    @classmethod
    def tokenize(cls, source_str):
        """
        Parse the source html into a list of tokens. Only tags and
        tags data are conserved, other elements such as comments are
        discarded.
        """
        tokenizer = cls()
        tokenizer.feed(source_str)
        return tokenizer.tokens


class TestHttpBase(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addClassCleanup(lazy_property.reset_all, odoo.http.root)
        cls.classPatch(odoo.conf, 'server_wide_modules', ['base', 'web', 'test_http'])
        lazy_property.reset_all(odoo.http.root)

    def db_url_open(self, url, *args, allow_redirects=False, **kwargs):
        return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def nodb_url_open(self, url, *args, allow_redirects=False, **kwargs):
        with patch('odoo.http.db_list') as db_list, \
             patch('odoo.http.db_filter') as db_filter, \
             patch('odoo.http.db_monodb') as db_monodb:
            db_list.return_value = []
            db_filter.return_value = []
            db_monodb.return_value = None
            return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)


@tagged('post_install', '-at_install')
class TestHttpGreeting(TestHttpBase):
    def test_greeting0_matrix(self):
        new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})
        test_matrix = [
            # path, database, login, expected_code, expected_re_pattern
            ('/test_http/greeting', False, None, 200, r"Tek'ma'te"),
            ('/test_http/greeting', True, None, 200, r"Tek'ma'te"),
            ('/test_http/greeting', True, 'public', 200, r"Tek'ma'te"),
            ('/test_http/greeting', True, 'jackoneill', 200, r"Tek'ma'te"),
            ('/test_http/greeting-none', False, None, 200, r"Tek'ma'te"),
            ('/test_http/greeting-none', True, None, 200, r"Tek'ma'te"),
            ('/test_http/greeting-none', True, 'public', 200, r"Tek'ma'te"),
            ('/test_http/greeting-none', True, 'jackoneill', 200, r"Tek'ma'te"),
            ('/test_http/greeting-public', False, None, 404, r"Not Found"),
            ('/test_http/greeting-public', True, None, 200, r"Tek'ma'te"),
            ('/test_http/greeting-public', True, 'public', 200, r"Tek'ma'te"),
            ('/test_http/greeting-public', True, 'jackoneill', 200, r"Tek'ma'te"),
            ('/test_http/greeting-user', False, None, 404, r"Not Found"),
            ('/test_http/greeting-user', True, None, 303, r".*/web/login.*"),
            ('/test_http/greeting-user', True, 'public', 303, r".*/web/login.*"),
            ('/test_http/greeting-user', True, 'jackoneill', 200, r"Tek'ma'te"),
        ]

        for path, withdb, login, expected_code, expected_pattern in test_matrix:
            with self.subTest(path=path, withdb=withdb, login=login):
                if withdb:
                    if login == 'public':
                        self.authenticate(None, None)
                    elif login:
                        self.authenticate(login, login)
                    res = self.db_url_open(path, allow_redirects=False)
                else:
                    res = self.nodb_url_open(path, allow_redirects=False)

                self.assertEqual(res.status_code, expected_code)
                self.assertRegex(res.text, expected_pattern)

                if withdb and login:
                    self.logout(keep_db=False)

    def test_greeting1_headers_nodb(self):
        res = self.nodb_url_open('/test_http/greeting')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'text/html; charset=utf-8')
        self.assertEqual(res.text, "Tek'ma'te")

    def test_greeting2_headers_db(self):
        new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})
        self.authenticate('jackoneill', 'jackoneill')
        res = self.db_url_open('/test_http/greeting')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'text/html; charset=utf-8')
        self.assertEqual(res.text, "Tek'ma'te")


@tagged('post_install', '-at_install')
class TestHttpStatic(TestHttpBase):
    def test_static0_png_image(self):
        res = self.nodb_url_open("/test_http/static/src/img/gizeh.png")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Length'), '814')
        self.assertEqual(res.headers.get('Content-Type'), 'image/png')
        cache_control = set(res.headers.get('Cache-Control', '').split(', '))
        self.assertEqual(cache_control, {'public', 'max-age=604800'})  # one week
        with file_open('test_http/static/src/img/gizeh.png', 'rb') as file:
            self.assertEqual(res.content, file.read())

    def test_static1_svg_image(self):
        res = self.nodb_url_open("/test_http/static/src/img/gizeh.svg")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Length'), '1529')
        self.assertEqual(res.headers.get('Content-Type'), 'image/svg+xml')
        cache_control = set(res.headers.get('Cache-Control', '').split(', '))
        self.assertEqual(cache_control, {'public', 'max-age=604800'})  # one week
        with file_open('test_http/static/src/img/gizeh.svg', 'rb') as file:
            self.assertEqual(res.content, file.read())

    def test_static2_not_found(self):
        res = self.nodb_url_open("/test_http/static/i-dont-exist")
        self.assertEqual(res.status_code, 404)

    def test_static3_attachment(self):
        with file_open('test_http/static/src/img/gizeh.svg', 'rb') as file:
            content = file.read()

        attachment = self.env['ir.attachment'].create({
            'name': 'point_of_origin.svg',
            'type': 'binary',
            'raw': content,
            'res_model': 'test_http.stargate',
            'res_id': self.ref('test_http.earth'),
        })
        attachment['url'] = f'/test_http/{attachment["checksum"]}'

        res = self.db_url_open(attachment['url'])
        self.assertEqual(res.headers.get('Content-Length'), '1529')
        self.assertEqual(res.headers.get('Content-Type'), 'image/svg+xml; charset=utf-8')
        self.assertEqual(res.headers.get('Content-Security-Policy'), "default-src 'none'")
        self.assertEqual(res.content, content)


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
        res = self.nodb_url_open('/test_http/echo-http-post', data='{}', headers=CT_JSON)
        self.assertIn("Bad Request", res.text)

    @unittest.skip("Broken in master, fixed in httpocalypse.")
    def test_echohttp5_post_csrf(self):
        res = self.nodb_url_open('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor'})
        self.assertEqual(res.status_code, 303)
        self.assertEqual(urlparse(res.headers.get('Location', '')).path, '/web/database/selector')


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
        res = self.db_url_open('/test_http/echo-http-post', data='{}', headers=CT_JSON)
        self.assertIn("Bad Request", res.text)

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
        res = self.db_url_open('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor', 'csrf_token': WebRequest.csrf_token(self)})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'race': 'Asgard', 'commander': 'Thor'}")



@tagged('post_install', '-at_install')
class TestHttpEchoReplyJsonWithDB(TestHttpBase):
    def setUp(self):
        super().setUp()
        self.jackoneill = new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})
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
        self.assertEqual(res.text, '{"jsonrpc": "2.0", "id": 0, "result": {"name": "Thor"}}')


@tagged('post_install', '-at_install')
class TestHttpModels(TestHttpBase):
    def setUp(self):
        super().setUp()
        self.jackoneill = new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})
        self.authenticate('jackoneill', 'jackoneill')

    def test_models0_galaxy_ok(self):
        milky_way = self.env.ref('test_http.milky_way')

        res = self.url_open(f"/test_http/{milky_way.id}")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            HtmlTokenizer.tokenize(res.text),
            HtmlTokenizer.tokenize('''\
                <p>Milky Way</p>
                <ul>
                    <li><a href="/test_http/1/1">Earth (P4X-126)</a></li>
                    <li><a href="/test_http/1/2">Abydos (P2X-125)</a></li>
                    <li><a href="/test_http/1/3">Dakara (P5C-113)</a></li>
                </ul>
                ''')
            )

    @unittest.skip('500 without website, 404 with website, 400 in httpocalypse. Cmon master...')
    def test_models1_galaxy_ko(self):
        res = self.url_open("/test_http/404")  # unknown galaxy
        self.assertEqual(res.status_code, 400)
        self.assertIn('The Ancients did not settle there.', res.text)

    def test_models2_stargate_ok(self):
        milky_way = self.env.ref('test_http.milky_way')
        earth = self.env.ref('test_http.earth')

        res = self.url_open(f'/test_http/{milky_way.id}/{earth.id}')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            HtmlTokenizer.tokenize(res.text),
            HtmlTokenizer.tokenize('''\
                <dl>
                    <dt>name</dt><dd>Earth</dd>
                    <dt>address</dt><dd>sq5Abt</dd>
                    <dt>sgc_designation</dt><dd>P4X-126</dd>
                </dl>
            ''')
        )

    @unittest.skip('500 without website, 404 with website, 400 in httpocalypse. Cmon master...')
    def test_models3_stargate_ko(self):
        milky_way = self.env.ref('test_http.milky_way')
        res = self.url_open(f'/test_http/{milky_way.id}/9999')  # unknown gate
        self.assertEqual(res.status_code, 400)
        self.assertIn("The goa'uld destroyed the gate", res.text)


@tagged('post_install', '-at_install')
class TestHttpMisc(TestHttpBase):
    @unittest.skip('In master it is in the http_routing override')
    def test_misc0_redirect(self):
        res = self.nodb_url_open('/test_http//greeting')
        self.assertEqual(res.status_code, 301)
        self.assertEqual(urlparse(res.headers.get('Location', '')).path, '/test_http/greeting')

    def test_misc1_reverse_proxy(self):
        # client <-> reverse-proxy <-> odoo
        client_ip = '127.0.0.16'
        reverseproxy_ip = gethostbyname(HOST)
        host = 'mycompany.odoo.com'

        headers = {
            'Host': '',
            'X-Forwarded-For': client_ip,
            'X-Forwarded-Host': host,
            'X-Forwarded-Proto': 'https'
        }

        # Don't trust client-sent forwarded headers
        with patch.object(config, 'options', {**config.options, 'proxy_mode': False}):
            res = self.nodb_url_open('/test_http/wsgi_environ', headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()['REMOTE_ADDR'], reverseproxy_ip)
            self.assertEqual(res.json()['HTTP_HOST'], '')

        # Trust proxy-sent forwarded headers
        with patch.object(config, 'options', {**config.options, 'proxy_mode': True}):
            res = self.nodb_url_open('/test_http/wsgi_environ', headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()['REMOTE_ADDR'], client_ip)
            self.assertEqual(res.json()['HTTP_HOST'], host)


@tagged('post_install', '-at_install')
class TestHttpCors(TestHttpBase):
    def test_cors0_http_default(self):
        res_opt = self.opener.options(f'{self.base_url()}/test_http/cors_http_default', timeout=10, allow_redirects=False)
        self.assertIn(res_opt.status_code, (200, 204))
        self.assertEqual(res_opt.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertEqual(res_opt.headers.get('Access-Control-Allow-Methods'), 'GET, POST')
        self.assertEqual(res_opt.headers.get('Access-Control-Max-Age'), '86400')  # one day
        self.assertEqual(res_opt.headers.get('Access-Control-Allow-Headers'), 'Origin, X-Requested-With, Content-Type, Accept, Authorization')

        res_get = self.url_open('/test_http/cors_http_default')
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertEqual(res_get.headers.get('Access-Control-Allow-Methods'), 'GET, POST')

    @unittest.skip("Broken in master, fixed in httpocalypse.")
    def test_cors1_http_methods(self):
        res_opt = self.opener.options(f'{self.base_url()}/test_http/cors_http_methods', timeout=10, allow_redirects=False)
        self.assertIn(res_opt.status_code, (200, 204))
        self.assertEqual(res_opt.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertEqual(res_opt.headers.get('Access-Control-Allow-Methods'), 'GET, PUT')
        self.assertEqual(res_opt.headers.get('Access-Control-Max-Age'), '86400')  # one day
        self.assertEqual(res_opt.headers.get('Access-Control-Allow-Headers'), 'Origin, X-Requested-With, Content-Type, Accept, Authorization')

        res_post = self.url_open('/test_http/cors_http_methods')
        self.assertEqual(res_post.status_code, 200)
        self.assertEqual(res_post.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertEqual(res_post.headers.get('Access-Control-Allow-Methods'), 'GET, PUT')

    def test_cors2_json(self):
        res_opt = self.opener.options(f'{self.base_url()}/test_http/cors_json', timeout=10, allow_redirects=False)
        self.assertIn(res_opt.status_code, (200, 204), res_opt.text)
        self.assertEqual(res_opt.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertEqual(res_opt.headers.get('Access-Control-Allow-Methods'), 'POST')
        self.assertEqual(res_opt.headers.get('Access-Control-Max-Age'), '86400')  # one day
        self.assertEqual(res_opt.headers.get('Access-Control-Allow-Headers'), 'Origin, X-Requested-With, Content-Type, Accept, Authorization')

        res_post = self.url_open('/test_http/cors_json', data=json.dumps({'params': {}}), headers=CT_JSON)
        self.assertEqual(res_post.status_code, 200)
        self.assertEqual(res_post.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertEqual(res_post.headers.get('Access-Control-Allow-Methods'), 'POST')
