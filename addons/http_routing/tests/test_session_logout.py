# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests import tagged, HttpCase, new_test_user


@tagged("-at_install", "post_install")
class TestSessionLogout(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_user = new_test_user(
            cls.env, name='Tapu',
            login='new_user',
            password='new_user',
            email='tapu@example.com',
        )

    def test_logout_via_get(self):
        """Test that GET /web/session/logout returns 303 and redirects to /odoo."""
        self.authenticate("new_user", "new_user")
        response = self.url_open("/web/session/logout", allow_redirects=False)
        self.assertEqual(
            response.status_code,
            303,
            "GET /web/session/logout should return 303 redirect",
        )
        self.assertTrue(
            response.headers.get("Location", "").endswith("/odoo"),
            "GET /web/session/logout should redirect to /odoo",
        )

    def test_logout_via_post(self):
        """Test that POST /web/session/logout returns 303 and redirects to /odoo."""
        self.authenticate("new_user", "new_user")
        response = self.url_open(
            "/web/session/logout",
            method="POST",
            data={"csrf_token": http.Request.csrf_token(self)},
            allow_redirects=False,
        )
        self.assertEqual(
            response.status_code,
            303,
            "POST /web/session/logout should return 303 redirect",
        )
        self.assertTrue(
            response.headers.get("Location", "").endswith("/odoo"),
            "POST /web/session/logout should redirect to /odoo",
        )
