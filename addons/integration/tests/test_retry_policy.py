from unittest.mock import Mock, patch

import requests
from urllib3.exceptions import MaxRetryError, ReadTimeoutError, ResponseError

from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import get_api_client
from odoo.addons.integration.tools.exceptions import CommTimeoutError, ServerError


@tagged("post_install", "-at_install", "integration")
class TestRetryPolicy(APITransportTestCase):
    def setUp(self):
        super().setUp()
        self.service_with_auth.write(
            {"retry_enabled": True, "retry_max_attempts": 3, "timeout_read": 20}
        )
        self.retry = get_api_client(self.env, "test_auth_api")._get_retry_config()

    def test_a_non_idempotent_call_is_not_resent_on_a_server_error(self):
        for method in ("POST", "PATCH"):
            with self.subTest(method=method):
                self.assertFalse(self.retry.is_retry(method, 503))
                self.assertFalse(self.retry.is_retry(method, 500))

    def test_a_non_idempotent_call_is_not_resent_after_a_read_timeout(self):
        self.assertFalse(self.retry._is_method_retryable("POST"))

    def test_a_rejected_non_idempotent_call_is_retried(self):
        self.assertTrue(self.retry.is_retry("POST", 429))

    def test_an_idempotent_call_is_still_retried(self):
        self.assertTrue(self.retry.is_retry("GET", 503))
        self.assertTrue(self.retry.is_retry("PUT", 502))

    def test_retry_after_is_capped_by_the_read_timeout(self):
        response = Mock(headers={"Retry-After": "3600"})

        self.assertEqual(self.retry.get_retry_after(response), 20)
        self.assertEqual(self.retry.new(total=1).get_retry_after(response), 20)

    def test_exhausted_status_retries_return_the_response_instead_of_raising(self):
        self.assertFalse(self.retry.raise_on_status)


@tagged("post_install", "-at_install", "integration")
class TestExhaustedRetriesKeepTheirKind(APITransportTestCase):
    def test_a_read_timeout_after_retries_is_a_timeout(self):
        exhausted = requests.exceptions.ConnectionError(
            MaxRetryError(
                None, "/slow", ReadTimeoutError(None, "/slow", "read timed out")
            )
        )
        with patch("requests.Session.request", side_effect=exhausted):
            with self.assertRaises(CommTimeoutError):
                get_api_client(self.env, "test_auth_api").post("/slow", json={})

    def test_a_persistent_server_error_is_a_server_error_with_its_status(self):
        with patch("requests.Session.request") as mock_request:
            mock_request.return_value = self.create_mock_response(
                status_code=503, json_data={"error": "unavailable"}
            )
            with self.assertRaises(ServerError) as caught:
                get_api_client(self.env, "test_auth_api").get("/busy")

        self.assertEqual(caught.exception.status_code, 503)

    def test_a_retry_error_still_reports_the_last_status(self):
        exhausted = requests.exceptions.RetryError(
            MaxRetryError(None, "/busy", ResponseError("too many 503 error responses"))
        )
        with patch("requests.Session.request", side_effect=exhausted):
            with self.assertRaises(ServerError):
                get_api_client(self.env, "test_auth_api").get("/busy")
