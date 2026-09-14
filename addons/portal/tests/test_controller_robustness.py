import logging

from odoo.exceptions import AccessDenied
from odoo.http import Request
from odoo.tests.common import HttpCase, JsonRpcException, tagged

from odoo.addons.mail.tests.common import mail_new_test_user

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestPortalControllerRobustness(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = mail_new_test_user(
            cls.env,
            "portal_robustness",
            groups="base.group_portal",
            name="Portal Robustness",
        )

    def _login(self):
        self.authenticate("portal_robustness", "portal_robustness")

    def test_security_post_missing_password_fields(self):
        self._login()
        response = self.url_open(
            "/my/security",
            data={"csrf_token": Request.csrf_token(self)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("You cannot leave any password empty.", response.text)

    def test_password_change_preserves_whitespace(self):
        old_password = "  portal old password  "
        new_password = "  portal new password  "
        self.portal_user.password = old_password
        self.authenticate(self.portal_user.login, old_password)

        response = self.url_open(
            "/my/security",
            data={
                "old": old_password,
                "new1": new_password,
                "new2": new_password,
                "csrf_token": Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, 200)
        _logger.debug(
            "Password change returned HTTP %s; verifying exact credentials",
            response.status_code,
        )
        self.portal_user.with_user(self.portal_user)._check_credentials(
            {
                "login": self.portal_user.login,
                "password": new_password,
                "type": "password",
            },
            {"interactive": True},
        )
        with self.assertRaises(AccessDenied):
            self.portal_user.with_user(self.portal_user)._check_credentials(
                {
                    "login": self.portal_user.login,
                    "password": new_password.strip(),
                    "type": "password",
                },
                {"interactive": True},
            )

        retained_session = self.url_open("/my/security", allow_redirects=False)
        self.assertEqual(retained_session.status_code, 200)
        self.authenticate(None, None)
        login = self.url_open(
            "/web/login",
            data={
                "login": self.portal_user.login,
                "password": new_password,
                "csrf_token": Request.csrf_token(self),
            },
            allow_redirects=False,
        )
        _logger.debug("Exact password login returned HTTP %s", login.status_code)
        self.assertEqual(login.status_code, 303)
        self.assertEqual(
            self.url_open("/my/security", allow_redirects=False).status_code, 200
        )

    def test_password_confirmation_compares_exact_text(self):
        self._login()
        response = self.url_open(
            "/my/security",
            data={
                "old": "portal_robustness",
                "new1": "  different spaces  ",
                "new2": "different spaces",
                "csrf_token": Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "The new password and its confirmation must be identical.", response.text
        )
        _logger.debug("Whitespace confirmation mismatch was rejected")
        self.portal_user.with_user(self.portal_user)._check_credentials(
            {
                "login": self.portal_user.login,
                "password": "portal_robustness",
                "type": "password",
            },
            {"interactive": True},
        )

    def test_address_form_non_numeric_partner_id(self):
        self._login()
        response = self.url_open("/my/address?partner_id=abc")
        self.assertEqual(response.status_code, 404)

    def test_address_submit_non_numeric_partner_id(self):
        self._login()
        response = self.url_open(
            "/my/address/submit",
            data={
                "partner_id": "abc",
                "csrf_token": Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_address_archive_non_numeric_partner_id(self):
        self._login()
        with self.assertRaises(JsonRpcException) as capture:
            self.call_jsonrpc("/my/address/archive", params={"partner_id": "abc"})
        self.assertNotIn("ValueError", str(capture.exception))

    def test_chatter_fetch_unknown_model(self):
        self._login()
        with self.assertRaises(JsonRpcException) as capture:
            self.call_jsonrpc(
                "/mail/chatter_fetch",
                params={"thread_model": "no.such.model", "thread_id": 1},
            )
        self.assertNotIn("KeyError", str(capture.exception))

    def test_chatter_fetch_model_without_portal_chatter(self):
        self._login()
        with self.assertRaises(JsonRpcException) as capture:
            self.call_jsonrpc(
                "/mail/chatter_fetch",
                params={"thread_model": "res.country", "thread_id": 1},
            )
        self.assertNotIn("KeyError", str(capture.exception))

    def test_mail_routes_non_numeric_id_no_valueerror(self):
        self._login()
        cases = [
            (
                "/mail/chatter_fetch",
                {"thread_model": "res.partner", "thread_id": "abc"},
            ),
            (
                "/portal/chatter_init",
                {"thread_model": "res.partner", "thread_id": "abc"},
            ),
            (
                "/mail/message/reaction",
                {"message_id": "abc", "content": "x", "action": "add"},
            ),
            (
                "/mail/message/post",
                {
                    "thread_model": "res.partner",
                    "thread_id": "abc",
                    "post_data": {"body": "hi"},
                },
            ),
            (
                "/mail/message/update_content",
                {"message_id": "abc", "update_data": {"body": "hi"}},
            ),
            ("/mail/update_is_internal", {"message_id": "abc", "is_internal": True}),
        ]
        for route, params in cases:
            with self.subTest(route=route):
                with self.assertRaises(JsonRpcException) as capture:
                    self.call_jsonrpc(route, params=params)
                self.assertNotIn("ValueError", str(capture.exception))
