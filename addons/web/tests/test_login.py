# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.http.session import session_store
from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


class TestWebLoginCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = new_test_user(cls.env, 'internal_user', context={'lang': 'en_US'})
        cls.portal_user = new_test_user(cls.env, 'portal_user', groups='base.group_portal')

    def setUp(self):
        super().setUp()
        self.authenticate(None, None)

    def login(self, username, password, csrf_token=None):
        """Log in with provided credentials and return response to POST request or raises for status."""
        res_post = self.url_open('/web/login', data={
            'login': username,
            'password': password,
            'csrf_token': csrf_token or self.csrf_token(),
        })
        res_post.raise_for_status()

        return res_post


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWebLogin(TestWebLoginCommon):
    def test_web_login(self):
        res_post = self.login('internal_user', 'internal_user')
        # ensure we are logged-in
        self.url_open(
            '/web/session/check',
            headers={'Content-Type': 'application/json'},
            data='{}',
        ).raise_for_status()
        # ensure we end up on the right page for internal users.
        self.assertEqual(res_post.request.path_url, '/odoo')

    def test_web_login_external(self):
        res_post = self.login('portal_user', 'portal_user')
        # ensure we end up on the right page for external users. Valid without portal installed.
        self.assertEqual(res_post.request.path_url, '/web/login_successful')

    def test_web_login_bad_xhr(self):
        # simulate the user downloaded the login form
        csrf_token = self.csrf_token()

        # simulate that the JS sended a bad XHR to a route that is
        # auth='none' using the same session (e.g. via a service worker)
        bad_xhr = self.url_open('/web/login_successful', allow_redirects=False)
        self.assertNotEqual(bad_xhr.status_code, 200)

        # log in using the above form, it should still be valid
        self.login('internal_user', 'internal_user', csrf_token)

    def test_web_switch_to_admin(self):
        session = self.authenticate(None, None)
        res = self.url_open('/web/become', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 303)
        self.assertURLEqual(res.headers['Location'], '/web/login?redirect=/web/become?')
        sid = res.cookies.get('session_id', session.sid)
        self.assertEqual(sid, session.sid, "it should not have a new session")
        self.assertIsNone(session_store().get(sid)['uid'], "it should still not be connected")

        session = self.authenticate('internal_user', 'internal_user')
        res = self.url_open('/web/become', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 303)
        self.assertURLEqual(res.headers['Location'], '/odoo')
        sid = res.cookies.get('session_id', session.sid)
        self.assertEqual(sid, session.sid, "it should not have a new session")
        self.assertEqual(session_store().get(sid)['uid'], self.internal_user.id,
            "it should not had become SUPERUSER")

        session = self.authenticate('admin', 'admin')
        res = self.url_open('/web/become', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 303)
        self.assertURLEqual(res.headers['Location'], '/odoo')
        sid = res.cookies.get('session_id', session.sid)
        # self.assertNotEqual(sid, session.sid, "it should have a new session")
        self.assertEqual(session_store().get(sid)['uid'], odoo.SUPERUSER_ID,
            "it should had become SUPERUSER")


@tagged('post_install', '-at_install')
class TestUserSwitch(HttpCaseWithUserDemo):
    def test_user_switch(self):
        self.start_tour('/odoo', 'test_user_switch', login='demo')
