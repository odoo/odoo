# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import http
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tests.common import get_db_name, HOST, HttpCase, new_test_user, Opener, tagged


class TestWebLoginCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        new_test_user(cls.env, 'internal_user', context={'lang': 'en_US'})
        new_test_user(cls.env, 'portal_user', groups='base.group_portal')

    def setUp(self):
        super().setUp()
        self.session = http.root.session_store.new()
        self.session.update(http.get_default_session(), db=get_db_name())
        self.opener = Opener(self)
        self.opener.cookies.set('session_id', self.session.sid, domain=HOST, path='/')

    def login(self, username, password, csrf_token=None):
        """Log in with provided credentials and return response to POST request or raises for status."""
        res_post = self.url_open('/web/login', data={
            'login': username,
            'password': password,
            'csrf_token':csrf_token or http.Request.csrf_token(self),
        })
        res_post.raise_for_status()

        return res_post


class TestWebLogin(TestWebLoginCommon):
    def test_web_login(self):
        res_post = self.login('internal_user', 'internal_user')
        # ensure we are logged-in
        self.url_open(
            '/web/session/check',
            headers={'Content-Type': 'application/json'},
            data='{}'
        ).raise_for_status()
        # ensure we end up on the right page for internal users.
        self.assertEqual(res_post.request.path_url, '/odoo')

    def test_web_login_external(self):
        res_post = self.login('portal_user', 'portal_user')
        # ensure we end up on the right page for external users. Valid without portal installed.
        self.assertEqual(res_post.request.path_url, '/web/login_successful')

    def test_web_login_bad_xhr(self):
        # simulate the user downloaded the login form
        csrf_token = http.Request.csrf_token(self)

        # simulate that the JS sended a bad XHR to a route that is
        # auth='none' using the same session (e.g. via a service worker)
        bad_xhr = self.url_open('/web/login_successful', allow_redirects=False)
        self.assertNotEqual(bad_xhr.status_code, 200)

        # log in using the above form, it should still be valid
        self.login('internal_user', 'internal_user', csrf_token)

    def test_web_login_case_insensitive(self):
        # Test that login is case insensitive
        login = '  InterNal_User  '
        res_post = self.login(login, 'internal_user')

        # ensure we are logged-in
        self.url_open(
            '/web/session/check',
            headers={'Content-Type': 'application/json'},
            data='{}'
        ).raise_for_status()
        # ensure we end up on the right page for internal users.
        self.assertEqual(res_post.request.path_url, '/odoo')

    def test_web_login_with_similar_logins(self):
        " Test that similar logins (case insensitive) are properly ordered by _get_login_order. "
        User = self.env['res.users']

        similar_logins = ['User', 'user', 'user2', 'USER2']
        users = User.with_context(force_lowercase_login=False).create([
            {'login': login, 'name': login, 'password': login}
            for login in similar_logins
        ])

        for idx, user in enumerate(users[:-1]):
            self.patch(self.env.cr, 'now', lambda: datetime.datetime.now() + datetime.timedelta(minutes=idx))
            User.with_user(user)._update_last_login()

        # Search those users and check that the order is correct
        similar_users = User.search(User._get_login_domain('user'), order=User._get_login_order())
        self.assertEqual(len(similar_users), 2)
        self.assertEqual(similar_users[0].login, 'user')
        self.assertGreater(similar_users[0].login_date, similar_users[1].login_date)

        # Check order for the similar logins involving null login dates.
        similar_users = User.search(User._get_login_domain('user2'), order=User._get_login_order())
        self.assertEqual(len(similar_users), 2)
        self.assertEqual(similar_users[0].login, 'user2')
        self.assertTrue(similar_users[0].login_date)
        self.assertFalse(similar_users[1].login_date)

        res_post = self.login('user', 'user')
        # ensure we are logged-in
        self.url_open(
            '/web/session/check',
            headers={'Content-Type': 'application/json'},
            data='{}'
        ).raise_for_status()
        # ensure we end up on the right page for internal users.
        self.assertEqual(res_post.request.path_url, '/odoo')


@tagged('post_install', '-at_install')
class TestUserSwitch(HttpCaseWithUserDemo):
    def test_user_switch(self):
        self.start_tour('/odoo', 'test_user_switch', login='demo')
