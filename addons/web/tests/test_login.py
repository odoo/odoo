# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests.common import get_db_name, HOST, HttpCase, new_test_user, Opener


class TestWebLoginCommon(HttpCase):
    def setUp(self):
        super().setUp()
        new_test_user(self.env, 'portal_user', groups='base.group_portal')

    def login(self, username, password):
        """Log in with provided credentials and return response to POST request or raises for status."""
        self.session = http.root.session_store.new()
        self.session.update(http.get_default_session(), db=get_db_name())
        self.opener = Opener(self.env.cr)
        self.opener.cookies.set('session_id', self.session.sid, domain=HOST, path='/')

        res_post = self.url_open('/web/login', data={
            'login': username,
            'password': password,
            'csrf_token': http.Request.csrf_token(self),
        })
        res_post.raise_for_status()

        return res_post


class TestWebLogin(TestWebLoginCommon):
    def test_web_login(self):
        new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})

        res_post = self.login('jackoneill', 'jackoneill')
        # ensure we are logged-in
        self.url_open(
            '/web/session/check',
            headers={'Content-Type': 'application/json'},
            data='{}'
        ).raise_for_status()
        # ensure we end up on the right page for internal users.
        self.assertEqual(res_post.request.path_url, '/web')

    def test_web_login_external(self):
        res_post = self.login('portal_user', 'portal_user')
        # ensure we end up on the right page for external users. Valid without portal installed.
        self.assertEqual(res_post.request.path_url, '/web/login_successful')
