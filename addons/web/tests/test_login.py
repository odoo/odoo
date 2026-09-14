from odoo import http
from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("web_http", "web_login")
class TestWebLoginCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        new_test_user(cls.env, "internal_user", context={"lang": "en_US"})
        new_test_user(cls.env, "portal_user", groups="base.group_portal")

    def setUp(self):
        super().setUp()
        self.authenticate(None, None)

    def login(self, username, password, csrf_token=None):
        res_post = self.url_open(
            "/web/login",
            data={
                "login": username,
                "password": password,
                "csrf_token": csrf_token or http.Request.csrf_token(self),
            },
        )
        res_post.raise_for_status()

        return res_post


class TestWebLogin(TestWebLoginCommon):
    def test_web_login(self):
        res_post = self.login("internal_user", "internal_user")
        self.url_open(
            "/web/session/check",
            headers={"Content-Type": "application/json"},
            data="{}",
        ).raise_for_status()
        self.assertEqual(res_post.request.path_url, "/odoo")

    def test_web_login_external(self):
        # web sends a non-internal user to /web/login_successful; portal, when
        # installed, overrides _login_redirect and its own test pins /my. What
        # web guarantees on every database: the user is logged in and lands
        # neither on the login page nor in the backend.
        res_post = self.login("portal_user", "portal_user")
        landing = res_post.request.path_url
        self.assertNotEqual(landing, "/web/login")
        self.assertFalse(landing.startswith("/odoo"), landing)
        self.url_open(
            "/web/session/check",
            headers={"Content-Type": "application/json"},
            data="{}",
        ).raise_for_status()

    def test_web_login_bad_xhr(self):
        csrf_token = http.Request.csrf_token(self)

        bad_xhr = self.url_open("/web/login_successful", allow_redirects=False)
        self.assertNotEqual(bad_xhr.status_code, 200)

        self.login("internal_user", "internal_user", csrf_token)


@tagged("post_install", "-at_install", "web_tour", "web_login")
class TestUserSwitch(HttpCaseWithUserDemo):
    def test_user_switch(self):
        self.start_tour("/odoo", "test_user_switch", login="demo")
