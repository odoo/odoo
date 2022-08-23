# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib

from odoo.tests import tagged
from odoo.tests.common import new_test_user, WsgiCase, HttpCase
from .test_common import nodb, HttpTestMixin


class GreetingMixin(HttpTestMixin):
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
                cm = nodb()
                if withdb:
                    if login == 'public':
                        self.authenticate(None, None)
                    elif login:
                        self.authenticate(login, login)
                    cm = contextlib.nullcontext()
                with cm:
                    res = self.opener.get(path, allow_redirects=False)

                self.assertEqual(res.status_code, expected_code)
                self.assertRegex(res.text, expected_pattern)

                if withdb and login:
                    self.logout(keep_db=False)

    @nodb()
    def test_greeting1_headers_nodb(self):
        res = self.opener.get('/test_http/greeting')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'text/html; charset=utf-8')
        self.assertEqual(res.text, "Tek'ma'te")

    def test_greeting2_headers_db(self):
        new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})
        self.authenticate('jackoneill', 'jackoneill')
        res = self.opener.get('/test_http/greeting')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'text/html; charset=utf-8')
        self.assertEqual(res.text, "Tek'ma'te")


class TestWsgiGreeting(GreetingMixin, WsgiCase):
    pass
@tagged('post_install', '-at_install')
class TestHttpGreeting(GreetingMixin, HttpCase):
    pass
