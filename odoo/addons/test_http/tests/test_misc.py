# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from io import StringIO
from socket import gethostbyname
from unittest.mock import patch
from urllib.parse import urlparse

import odoo
from odoo.http import root, content_disposition
from odoo.tests import tagged
from odoo.tests.common import HOST, new_test_user, get_db_name, BaseCase
from odoo.tools import config, file_path, parse_version
from odoo.addons.test_http.controllers import CT_JSON

from odoo.addons.test_http.utils import TEST_IP
from .test_common import TestHttpBase

try:
    from importlib import metadata
    werkzeug_version = metadata.version('werkzeug')
except ImportError:
    import werkzeug
    werkzeug_version = werkzeug.__version__


@tagged('post_install', '-at_install')
class TestHttpMisc(TestHttpBase):
    def test_misc0_redirect(self):
        res = self.nodb_url_open('/test_http//greeting')
        awaited_codes = [404]
        if parse_version('2.2.0') <= parse_version(werkzeug_version) <= parse_version('3.0.1'):
            # Bug in werkzeug from 2.2.0 up to 3.0.1 (shipped in Ubuntu Noble 24.04)
            # not a big deal but should be removed once fixed upstream.
            awaited_codes.append(308)
        self.assertIn(res.status_code, awaited_codes)

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

    def test_misc2_local_redirect(self):
        def local_redirect(path):
            fake_req = odoo.tools.misc.DotDict(db=False)
            return odoo.http.Request.redirect(fake_req, path, local=True).headers['Location']
        self.assertEqual(local_redirect('https://www.example.com/hello?a=b'), '/hello?a=b')
        self.assertEqual(local_redirect('/hello?a=b'), '/hello?a=b')
        self.assertEqual(local_redirect('hello?a=b'), '/hello?a=b')
        self.assertEqual(local_redirect('www.example.com/hello?a=b'), '/www.example.com/hello?a=b')
        self.assertEqual(local_redirect('https://www.example.comhttps://www.example2.com/hello?a=b'), '/www.example2.com/hello?a=b')
        self.assertEqual(local_redirect('https://https://www.example.com/hello?a=b'), '/www.example.com/hello?a=b')

    def test_misc3_is_static_file(self):
        uri = 'test_http/static/src/img/gizeh.png'
        path = file_path(uri)

        # Valid URLs
        self.assertEqual(root.get_static_file(f'/{uri}'), path, "Valid file")
        self.assertEqual(root.get_static_file(f'odoo.com/{uri}', host='odoo.com'), path, "Valid file with valid host")
        self.assertEqual(root.get_static_file(f'http://odoo.com/{uri}', host='odoo.com'), path, "Valid file with valid host")

        # Invalid URLs
        self.assertIsNone(root.get_static_file('/test_http/i-dont-exist'), "File doesn't exist")
        self.assertIsNone(root.get_static_file('/test_http/__manifest__.py'), "File is not static")
        self.assertIsNone(root.get_static_file(f'odoo.com/{uri}'), "No host allowed")
        self.assertIsNone(root.get_static_file(f'http://odoo.com/{uri}'), "No host allowed")

    def test_misc4_rpc_qweb(self):
        jack = new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})
        milky_way = self.env.ref('test_http.milky_way')

        payload = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': None, 'params': {
            'service': 'object', 'method': 'execute', 'args': [
                get_db_name(), jack.id, 'jackoneill', 'test_http.galaxy', 'render', milky_way.id
            ]
        }})

        for method in (self.db_url_open, self.nodb_url_open):
            with self.subTest(method=method.__name__):
                res = method('/jsonrpc', data=payload, headers=CT_JSON)
                res.raise_for_status()

                res_rpc = res.json()
                self.assertNotIn('error', res_rpc.keys(), res_rpc.get('error', {}).get('data', {}).get('message'))
                self.assertIn(milky_way.name, res_rpc['result'], "QWeb template was correctly rendered")

    def test_misc5_geoip(self):
        res = self.nodb_url_open('/test_http/geoip')
        res.raise_for_status()
        self.assertEqual(res.json(), {
            'city': None,
            'country_code': None,
            'country_name': None,
            'latitude': None,
            'longitude': None,
            'region': None,
            'time_zone': None,
        })

        # Fake client IP using proxy_mode and a forged X-Forwarded-For http header
        headers = {
            'Host': '',
            'X-Forwarded-For': TEST_IP,
            'X-Forwarded-Host': 'odoo.com',
            'X-Forwarded-Proto': 'https'
        }
        with patch.dict('odoo.tools.config.options', {'proxy_mode': True}):
            res = self.nodb_url_open('/test_http/geoip', headers=headers)
            res.raise_for_status()
            self.assertEqual(res.json(), {
                'city': None,
                'country_code': 'FR',
                'country_name': 'France',
                'latitude': 48.8582,
                'longitude': 2.3387,
                'region': None,
                'time_zone': 'Europe/Paris',
            })

    def test_misc6_upload_file_retry(self):
        from odoo.addons.test_http import controllers  # pylint: disable=C0415

        with patch.object(controllers, "should_fail", True), StringIO("Hello world!") as file:
            res = self.url_open("/test_http/upload_file", files={"ufile": file}, timeout=None)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.text, file.getvalue())

    def test_misc7_robotstxt(self):
        self.nodb_url_open('/robots.txt').raise_for_status()

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
        self.opener.cookies['session_id'] = new_session.sid
        res = self.multidb_url_open('/test_http/ensure_db')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, 'db1')

class TestContentDisposition(BaseCase):

    def test_content_disposition(self):
        """ Test that content_disposition filename conforms to RFC 6266, RFC 5987 """
        assertions = [
            ('foo bar.xls', 'foo%20bar.xls', 'Space character'),
            ('foo(bar).xls', 'foo%28bar%29.xls', 'Parenthesis'),
            ('foo<bar>.xls', 'foo%3Cbar%3E.xls', 'Angle brackets'),
            ('foo[bar].xls', 'foo%5Bbar%5D.xls', 'Brackets'),
            ('foo{bar}.xls', 'foo%7Bbar%7D.xls', 'Curly brackets'),
            ('foo@bar.xls', 'foo%40bar.xls', 'At sign'),
            ('foo,bar.xls', 'foo%2Cbar.xls', 'Comma sign'),
            ('foo;bar.xls', 'foo%3Bbar.xls', 'Semicolon sign'),
            ('foo:bar.xls', 'foo%3Abar.xls', 'Colon sign'),
            ('foo\\bar.xls', 'foo%5Cbar.xls', 'Backslash sign'),
            ('foo"bar.xls', 'foo%22bar.xls', 'Double quote sign'),
            ('foo/bar.xls', 'foo%2Fbar.xls', 'Slash sign'),
            ('foo?bar.xls', 'foo%3Fbar.xls', 'Question mark'),
            ('foo=bar.xls', 'foo%3Dbar.xls', 'Equal sign'),
            ('foo*bar.xls', 'foo%2Abar.xls', 'Star sign'),
            ("foo'bar.xls", 'foo%27bar.xls', 'Single-quote sign'),
            ('foo%bar.xls', 'foo%25bar.xls', 'Percent sign'),
        ]
        for filename, pct_encoded, hint in assertions:
            self.assertEqual(content_disposition(filename), f"attachment; filename*=UTF-8''{pct_encoded}", f'{hint} should be percent encoded')
