# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch
from urllib.parse import urlparse
from socket import gethostbyname

import odoo
from odoo.http import Request, Session
from odoo.tests import tagged
from odoo.tests.common import HOST, HttpCase, new_test_user
from odoo.tools import config, file_open, mute_logger
from odoo.tools.func import lazy_property
from odoo.addons.test_http.controllers import CT_JSON
from odoo.addons.test_http.utils import (
    MemoryGeoipResolver, MemorySessionStore, HtmlTokenizer
)

GEOIP_ODOO_FARM_2 = {
    'city': 'Ramillies',
    'country_code': 'BE',
    'country_name': 'Belgium',
    'latitude': 50.6314,
    'longitude': 4.8573,
    'region': 'WAL',
    'time_zone': 'Europe/Brussels'
}


class TestHttpBase(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addClassCleanup(lazy_property.reset_all, odoo.http.root)
        cls.classPatch(odoo.conf, 'server_wide_modules', ['base', 'web', 'test_http'])
        lazy_property.reset_all(odoo.http.root)
        cls.classPatch(odoo.http.root, 'session_store', MemorySessionStore(session_class=Session))
        cls.classPatch(odoo.http.root, 'geoip_resolver', MemoryGeoipResolver())

    def setUp(self):
        super().setUp()
        odoo.http.root.session_store.store.clear()

    def db_url_open(self, url, *args, allow_redirects=False, **kwargs):
        return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def nodb_url_open(self, url, *args, allow_redirects=False, **kwargs):
        with patch('odoo.http.db_list') as db_list, \
             patch('odoo.http.db_filter') as db_filter:
            db_list.return_value = []
            db_filter.return_value = []
            return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def multidb_url_open(self, url, *args, allow_redirects=False, dblist=(), **kwargs):
        dblist = dblist or self.db_list
        assert len(dblist) >= 2, "There should be at least 2 databases"
        with patch('odoo.http.db_list') as db_list, \
             patch('odoo.http.db_filter') as db_filter, \
             patch('odoo.http.Registry') as Registry:
            db_list.return_value = dblist
            db_filter.side_effect = lambda dbs, host=None: [db for db in dbs if db in dblist]
            Registry.return_value = self.registry
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
        self.assertEqual(res.headers.get('Content-Type'), 'image/svg+xml; charset=utf-8')
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
        res = self.db_url_open('/test_http/echo-http-csrf?race=Asgard', data={'commander': 'Thor', 'csrf_token': Request.csrf_token(self)})
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

    @mute_logger('odoo.http')
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

    @mute_logger('odoo.http')
    def test_models3_stargate_ko(self):
        milky_way = self.env.ref('test_http.milky_way')
        res = self.url_open(f'/test_http/{milky_way.id}/9999')  # unknown gate
        self.assertEqual(res.status_code, 400)
        self.assertIn("The goa'uld destroyed the gate", res.text)


@tagged('post_install', '-at_install')
class TestHttpMisc(TestHttpBase):
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

@tagged('post_install', '-at_install')
class TestHttpEnsureDb(TestHttpBase):
    def setUp(self):
        super().setUp()
        self.db_list = ['db0', 'db1']

    def test_ensure_db0_db_selector(self):
        res = self.multidb_url_open('/test_http/ensure_db')
        res.raise_for_status()
        self.assertEqual(res.status_code, 303)
        self.assertEqual(urlparse(res.headers.get('Location', '')).path, '/web/database/selector')

    def test_ensure_db1_grant_db(self):
        res = self.multidb_url_open('/test_http/ensure_db?db=db0', timeout=10000)
        res.raise_for_status()
        self.assertEqual(res.status_code, 302)
        self.assertEqual(urlparse(res.headers.get('Location', '')).path, '/test_http/ensure_db')
        self.assertEqual(odoo.http.root.session_store.get(res.cookies['session_id']).db, 'db0')

        # follow the redirection
        res = self.multidb_url_open('/test_http/ensure_db')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, 'db0')

    def test_ensure_db2_use_session_db(self):
        session = self.authenticate(None, None)
        session.db = 'db0'
        odoo.http.root.session_store.save(session)

        res = self.multidb_url_open('/test_http/ensure_db')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, 'db0')

    def test_ensure_db3_change_db(self):
        session = self.authenticate(None, None)
        session.db = 'db0'
        odoo.http.root.session_store.save(session)

        res = self.multidb_url_open('/test_http/ensure_db?db=db1')
        res.raise_for_status()
        self.assertEqual(res.status_code, 302)
        self.assertEqual(urlparse(res.headers.get('Location', '')).path, '/test_http/ensure_db')

        new_session = odoo.http.root.session_store.get(res.cookies['session_id'])
        self.assertNotEqual(session.sid, new_session.sid)
        self.assertEqual(new_session.db, 'db1')
        self.assertEqual(new_session.uid, None)

        # follow redirection
        res = self.multidb_url_open('/test_http/ensure_db')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, 'db1')


class TestHttpSession(TestHttpBase):

    @mute_logger('odoo.http')  # greeting_none called ignoring args {'debug'}
    def test_session0_debug_mode(self):
        session = self.authenticate(None, None)
        self.assertEqual(session.debug, '')
        self.db_url_open('/test_http/greeting').raise_for_status()
        self.assertEqual(session.debug, '')
        self.db_url_open('/test_http/greeting?debug=1').raise_for_status()
        self.assertEqual(session.debug, '1')
        self.db_url_open('/test_http/greeting').raise_for_status()
        self.assertEqual(session.debug, '1')
        self.db_url_open('/test_http/greeting?debug=').raise_for_status()
        self.assertEqual(session.debug, '')

    def test_session1_default_session(self):
        # The default session should not be saved on the filestore.
        with patch.object(odoo.http.root.session_store, 'save') as mock_save:
            res = self.db_url_open('/test_http/greeting')
            res.raise_for_status()
            try:
                mock_save.assert_not_called()
            except AssertionError as exc:
                msg = f'save() was called with args: {mock_save.call_args}'
                raise AssertionError(msg) from exc

    def test_session2_geoip(self):
        real_save = odoo.http.root.session_store.save
        with patch.object(odoo.http.root.geoip_resolver, 'resolve') as mock_resolve,\
             patch.object(odoo.http.root.session_store, 'save') as mock_save:
            mock_resolve.return_value = GEOIP_ODOO_FARM_2
            mock_save.side_effect = real_save

            # Geoip is lazy: it should be computed only when necessary.
            self.nodb_url_open('/test_http/greeting').raise_for_status()
            mock_resolve.assert_not_called()

            # Geoip is like the defaut session: the session should not
            # be stored only due to geoip.
            mock_resolve.reset_mock()
            mock_save.reset_mock()
            res = self.nodb_url_open('/test_http/geoip')
            res.raise_for_status()
            self.assertEqual(res.text, str(GEOIP_ODOO_FARM_2))
            mock_save.assert_not_called()

            # Geoip is cached on the session: we shouldn't geolocate the
            # same ip multiple times.
            mock_resolve.reset_mock()
            mock_save.reset_mock()
            self.nodb_url_open('/test_http/save_session').raise_for_status()
            self.nodb_url_open('/test_http/geoip').raise_for_status()
            res = self.nodb_url_open('/test_http/geoip')
            res.raise_for_status()
            self.assertEqual(res.text, str(GEOIP_ODOO_FARM_2))
            mock_resolve.assert_called_once()

class TestHttpJsonError(TestHttpBase):

    jsonrpc_error_structure = {
        'error': {
            'code': ...,
            'data': {
                'arguments': ...,
                'context': ...,
                'debug': ...,
                'message': ...,
                'name': ...,
            },
            'message': ...,
        },
        'id': ...,
        'jsonrpc': ...,
    }

    def assertIsErrorPayload(self, payload):
        self.assertEqual(
            set(payload),
            set(self.jsonrpc_error_structure),
        )
        self.assertEqual(
            set(payload['error']),
            set(self.jsonrpc_error_structure['error']),
        )
        self.assertEqual(
            set(payload['error']['data']),
            set(self.jsonrpc_error_structure['error']['data']),
        )


    @mute_logger('odoo.http')
    def test_errorjson0_value_error(self):
        res = self.db_url_open('/test_http/json_value_error',
            data=json.dumps({'jsonrpc': '2.0', 'id': 1234, 'params': {}}),
            headers=CT_JSON
        )
        res.raise_for_status()

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type', ''), 'application/json')

        payload = res.json()
        self.assertIsErrorPayload(payload)

        error_data = payload['error']['data']
        self.assertEqual(error_data['name'], 'builtins.ValueError')
        self.assertEqual(error_data['message'], 'Unknown destination')
        self.assertEqual(error_data['arguments'], ['Unknown destination'])
        self.assertEqual(error_data['context'], {})

    @mute_logger('odoo.http')
    def test_errorjson1_dev_mode_werkzeug(self):
        with patch.object(config, 'options', {**config.options, 'dev_mode': 'werkzeug'}):
            self.test_errorjson0_value_error()
