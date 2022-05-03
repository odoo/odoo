from odoo.tools import mute_logger
from .test_http import TestHttpBase


class TestHttpErrorHttp(TestHttpBase):
    @mute_logger('odoo.http')  # UserError("Walter is AFK")
    def test_httperror0_exceptions_as_404(self):
        with self.subTest('Decorator/AccessError'):
            res = self.nodb_url_open('/test_http/hide_errors/decorator?error=AccessError')
            self.assertEqual(res.status_code, 404, "AccessError are configured to be hidden, they should be re-thrown as NotFound")
            self.assertNotIn("Wrong iris code", res.text, "The real AccessError message should be hidden.")

        with self.subTest('Decorator/UserError'):
            res = self.nodb_url_open('/test_http/hide_errors/decorator?error=UserError')
            self.assertEqual(res.status_code, 400, "UserError are not configured to be hidden, they should be kept as-is.")
            self.assertIn("Walter is AFK", res.text, "The real UserError message should be kept")

        with self.subTest('Context-Manager/AccessError'):
            res = self.nodb_url_open('/test_http/hide_errors/context-manager?error=AccessError')
            self.assertEqual(res.status_code, 404, "AccessError are configured to be hidden, they should be re-thrown as NotFound")
            self.assertNotIn("Wrong iris code", res.text, "The real AccessError message should be hidden.")

        with self.subTest('Context-Manager/UserError'):
            res = self.nodb_url_open('/test_http/hide_errors/context-manager?error=UserError')
            self.assertEqual(res.status_code, 400, "UserError are not configured to be hidden, they should be kept as-is.")
            self.assertIn("Walter is AFK", res.text, "The real UserError message should be kept")
