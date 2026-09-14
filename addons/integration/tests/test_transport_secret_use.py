from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import get_api_client


@tagged("post_install", "-at_install", "integration")
class TestTransportDoesNotSpendTheRevealAllowance(APITransportTestCase):
    def _call_past_the_cap(self, credential, code, calls=4):
        credential.write(
            {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": 2}
        )
        with patch("requests.Session.request") as mock_request:
            mock_request.return_value = self.create_mock_response(json_data={})
            for _ in range(calls):
                self.env.invalidate_all()
                get_api_client(self.env, code).get("/resource")
        return mock_request.call_args[1]

    def test_bearer_calls_past_the_decrypt_cap_still_authenticate(self):
        sent = self._call_past_the_cap(self.credential_bearer, "test_auth_api")

        self.assertEqual(sent["headers"]["Authorization"], "Bearer bearer_token_xyz")

    def test_basic_auth_calls_past_the_decrypt_cap_still_authenticate(self):
        sent = self._call_past_the_cap(self.credential_basic, "test_basic_auth")

        self.assertEqual(sent["auth"], ("testuser", "testpass123"))

    def test_transport_use_writes_no_reveal_rows(self):
        before = self.env["credential.access.log"].search_count(
            [
                ("credential_id", "=", self.credential_bearer.id),
                ("operation", "=", "read"),
            ]
        )

        self._call_past_the_cap(self.credential_bearer, "test_auth_api", calls=3)

        after = self.env["credential.access.log"].search_count(
            [
                ("credential_id", "=", self.credential_bearer.id),
                ("operation", "=", "read"),
            ]
        )
        self.assertEqual(after, before)
