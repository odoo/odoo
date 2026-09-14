from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import get_api_client
from odoo.addons.integration.tools.exceptions import ServerError


@tagged("post_install", "-at_install", "integration")
class TestExchangeLogSurvivesRollback(APITransportTestCase):
    def _fail_a_call(self, trace_id):
        with patch("requests.Session.request") as mock_request:
            mock_request.return_value = self.create_mock_response(
                status_code=500, json_data={"error": "boom"}
            )
            with self.assertRaises(ServerError):
                get_api_client(self.env, "test_auth_api").get(
                    "/boom", trace_id=trace_id
                )

    def _rows(self, trace_id):
        return (
            self.env["integration.exchange"]
            .sudo()
            .search_count([("trace_id", "=", trace_id)])
        )

    def _roll_back_the_callers_transaction(self):
        cr = self.env.cr
        cr.clear()
        with self.enter_registry_test_mode():
            cr.postrollback.run()

    def test_a_failed_call_is_logged_even_when_the_caller_rolls_back(self):
        self._fail_a_call("rollback-trace")

        self._roll_back_the_callers_transaction()

        self.assertEqual(self._rows("rollback-trace"), 1)

    def test_a_committed_transaction_does_not_log_twice(self):
        self._fail_a_call("commit-trace")

        self.env.cr.precommit.run()
        self.env.cr.postrollback.clear()

        self.assertEqual(self._rows("commit-trace"), 1)
