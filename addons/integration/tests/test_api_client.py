import contextlib
from unittest.mock import patch

import requests

from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import (
    OutboundAPIClient,
    get_api_client,
)
from odoo.addons.integration.tools.exceptions import (
    AuthenticationError,
    CommError,
    RateLimitError,
)


@tagged("post_install", "-at_install", "integration")
class TestAPIClient(APITransportTestCase):
    def test_get_api_client_success(self):
        client = get_api_client(self.env, "test_stripe")

        self.assertIsNotNone(client)
        self.assertIsInstance(client, OutboundAPIClient)
        self.assertEqual(client.endpoint_code, "test_stripe")
        self.assertEqual(client.service.id, self.service_stripe.id)
        self.assertEqual(client.credential.id, self.credential_stripe.id)

    def test_get_api_client_nonexistent_service(self):
        with self.assertRaises(Exception) as context:
            get_api_client(self.env, "nonexistent_service")

        self.assertIn("not found", str(context.exception))

    def test_get_api_client_no_credential(self):
        self.env["integration.service"].create(
            {
                "name": "No Credential Service",
                "code": "test_no_cred",
                "category": "other",
                "endpoint_url": "https://api.test.com",
                "environment": "production",
                "company_id": self.env.company.id,
                "auth_type": "bearer",
            }
        )

        with self.assertRaises(CommError) as context:
            get_api_client(self.env, "test_no_cred")

        self.assertIn("No active credentials", str(context.exception))

    def test_get_api_client_with_company(self):
        credential_a = self.env["credential.credential"].create(
            {
                "name": "Company A Credential",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.company_a.id,
                "category_id": self.cat_custom.id,
                "environment": "test",
                "credential_value": "sk_test_company_a",
            }
        )

        client = get_api_client(self.env, "test_stripe", company_id=self.company_a.id)

        self.assertEqual(client.credential.id, credential_a.id)
        self.assertEqual(client.credential.company_id.id, self.company_a.id)

    def test_url_building(self):
        client = get_api_client(self.env, "test_stripe")

        url = client._get_url("/customers")
        self.assertEqual(url, "https://api.stripe.test/v1/customers")

        url = client._get_url("customers")
        self.assertEqual(url, "https://api.stripe.test/v1/customers")

        url = client._get_url("/customers/123/charges")
        self.assertEqual(url, "https://api.stripe.test/v1/customers/123/charges")

    def test_full_url_endpoint(self):
        client = get_api_client(self.env, "test_stripe")
        full_url = "https://other-api.com/endpoint"

        url = client._get_url(full_url)
        self.assertEqual(url, full_url)


@tagged("post_install", "-at_install", "integration")
class TestRetryBackoffShape(APITransportTestCase):
    """`retry_backoff_type` must change the shape of the HTTP-level retry,
    not just the queue-level one (`get_retry_delay`): a `fixed` or
    `linear` endpoint used to get the same exponential curve as an
    `exponential` one because `urllib3.Retry` only knows exponential."""

    class _FakeHistoryEntry:
        redirect_location = None

    def _backoff_curve(self, backoff_type, n=3):
        self.service_stripe.write(
            {"retry_enabled": True, "retry_backoff_type": backoff_type}
        )
        client = get_api_client(self.env, "test_stripe")
        retry = client._get_retry_config()

        curve = []
        for _ in range(n):
            retry.history = (*retry.history, self._FakeHistoryEntry())
            curve.append(retry.get_backoff_time())
        return curve

    def test_fixed_backoff_does_not_grow(self):
        self.assertEqual(self._backoff_curve("fixed"), [0, 1.0, 1.0])

    def test_linear_backoff_grows_by_a_constant_step(self):
        self.assertEqual(self._backoff_curve("linear"), [0, 1.0, 2.0])

    def test_exponential_backoff_doubles(self):
        self.assertEqual(self._backoff_curve("exponential"), [0, 4.0, 8.0])

    def test_fixed_and_linear_are_no_longer_identical(self):
        self.assertNotEqual(self._backoff_curve("fixed"), self._backoff_curve("linear"))


@tagged("post_install", "-at_install", "integration")
class TestURLValidation(APITransportTestCase):
    def _client_for(self, base_url):
        client = get_api_client(self.env, "test_stripe")
        client.base_url = base_url
        return client

    def test_port_above_the_valid_range_is_rejected(self):
        client = self._client_for("https://api.example.com:99999")
        with self.assertRaises(ValueError):
            client._get_url("/x")

    def test_port_zero_is_rejected(self):
        client = self._client_for("https://api.example.com:0")
        with self.assertRaises(ValueError):
            client._get_url("/x")

    def test_malformed_dotted_quad_is_rejected(self):
        client = self._client_for("http://192.168.1.300")
        with self.assertRaises(ValueError):
            client._get_url("/x")

    def test_dotless_internal_hostname_is_accepted(self):
        client = self._client_for("https://internal-host")
        self.assertEqual(client._get_url("/x"), "https://internal-host/x")

    def test_ipv6_literal_is_accepted(self):
        client = self._client_for("https://[::1]:8069")
        self.assertEqual(client._get_url("/x"), "https://[::1]:8069/x")

    def test_valid_port_is_accepted(self):
        client = self._client_for("https://api.example.com:8069")
        self.assertEqual(client._get_url("/x"), "https://api.example.com:8069/x")


@tagged("post_install", "-at_install", "integration")
class TestAPIClientAuthentication(APITransportTestCase):
    @patch("requests.Session.request")
    def test_bearer_token_auth(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"success": True}
        )

        client = get_api_client(self.env, "test_auth_api")
        client.get("/test")

        call_args = mock_request.call_args
        headers = call_args[1].get("headers", {})
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Bearer "))

    @patch("requests.Session.request")
    def test_basic_auth(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"success": True}
        )

        client = get_api_client(self.env, "test_basic_auth")
        client.get("/test")

        call_args = mock_request.call_args
        self.assertIsNotNone(call_args[1].get("auth"))

    @patch("requests.Session.request")
    def test_api_key_auth(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"success": True}
        )

        client = get_api_client(self.env, "test_cache")
        response = client.get("/test")

        self.assertEqual(response["status_code"], 200)

    @patch("requests.Session.request")
    def test_no_auth(self, mock_request):
        service_no_auth = self.env["integration.service"].create(
            {
                "name": "No Auth Service",
                "code": "test_no_auth",
                "category": "other",
                "endpoint_url": "https://api.public.com",
                "environment": "production",
                "company_id": self.env.company.id,
                "auth_type": "none",
            }
        )

        self.env["credential.credential"].create(
            {
                "name": "No Auth Credential",
                "endpoint_id": service_no_auth.id,
                "company_id": self.env.company.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "credential_value": "no_auth_placeholder",
            }
        )

        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "public"}
        )

        client = get_api_client(self.env, "test_no_auth")
        client.get("/public")

        call_args = mock_request.call_args
        headers = call_args[1].get("headers", {})
        self.assertNotIn("Authorization", headers)


@tagged("post_install", "-at_install", "integration")
class TestAPIClientHTTPMethods(APITransportTestCase):
    @patch("requests.Session.request")
    def test_get_request(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"id": 1, "name": "Test"}
        )

        client = get_api_client(self.env, "test_stripe")
        response = client.get("/customers/1")

        self.assertSuccessResponse(response)
        self.assertEqual(response["body"]["id"], 1)
        self.assertEqual(response["body"]["name"], "Test")

        self.assertEqual(
            mock_request.call_args.kwargs.get(
                "method",
                mock_request.call_args.args[0] if mock_request.call_args.args else None,
            ),
            "GET",
        )

    @patch("requests.Session.request")
    def test_post_request(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=201, json_data={"id": 123, "created": True}
        )

        client = get_api_client(self.env, "test_stripe")
        response = client.post("/customers", json={"name": "New Customer"})

        self.assertEqual(response["status_code"], 201)
        self.assertEqual(response["body"]["id"], 123)

        self.assertEqual(
            mock_request.call_args.kwargs.get(
                "method",
                mock_request.call_args.args[0] if mock_request.call_args.args else None,
            ),
            "POST",
        )

        call_kwargs = mock_request.call_args[1]
        self.assertIn("json", call_kwargs)
        self.assertEqual(call_kwargs["json"]["name"], "New Customer")

    @patch("requests.Session.request")
    def test_put_request(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"id": 1, "updated": True}
        )

        client = get_api_client(self.env, "test_stripe")
        response = client.put("/customers/1", json={"name": "Updated Name"})

        self.assertSuccessResponse(response)
        self.assertEqual(
            mock_request.call_args.kwargs.get(
                "method",
                mock_request.call_args.args[0] if mock_request.call_args.args else None,
            ),
            "PUT",
        )

    @patch("requests.Session.request")
    def test_patch_request(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"id": 1, "patched": True}
        )

        client = get_api_client(self.env, "test_stripe")
        response = client.patch("/customers/1", json={"email": "new@email.com"})

        self.assertSuccessResponse(response)
        self.assertEqual(
            mock_request.call_args.kwargs.get(
                "method",
                mock_request.call_args.args[0] if mock_request.call_args.args else None,
            ),
            "PATCH",
        )

    @patch("requests.Session.request")
    def test_delete_request(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=204, json_data={"deleted": True}
        )

        client = get_api_client(self.env, "test_stripe")
        response = client.delete("/customers/1")

        self.assertEqual(response["status_code"], 204)
        self.assertEqual(
            mock_request.call_args.kwargs.get(
                "method",
                mock_request.call_args.args[0] if mock_request.call_args.args else None,
            ),
            "DELETE",
        )


@tagged("post_install", "-at_install", "integration")
class TestClientErrorHandling(APITransportTestCase):
    @patch("requests.Session.request")
    def test_http_404_error(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=404, json_data={"error": "Not found"}
        )

        client = get_api_client(self.env, "test_stripe")

        with self.assertRaises(CommError) as context:
            client.get("/nonexistent")

        self.assertIn("Not found", str(context.exception))

    @patch("requests.Session.request")
    def test_http_500_error(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=500, json_data={"error": "Internal server error"}
        )

        client = get_api_client(self.env, "test_stripe")

        with self.assertRaises(CommError) as context:
            client.get("/test")

        self.assertIn("Server error", str(context.exception))

    @patch("requests.Session.request")
    def test_http_401_authentication_error(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=401, json_data={"error": "Unauthorized"}
        )

        client = get_api_client(self.env, "test_stripe")

        with self.assertRaises(AuthenticationError) as context:
            client.get("/test")

        self.assertIn("Authentication failed", str(context.exception))

    @patch("requests.Session.request")
    def test_http_429_rate_limit_error(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=429,
            json_data={"error": "Rate limit exceeded"},
            headers={"Retry-After": "60"},
        )

        client = get_api_client(self.env, "test_stripe")

        with self.assertRaises(RateLimitError) as context:
            client.get("/test")

        self.assertIn("Rate limit exceeded", str(context.exception))

    @patch("requests.Session.request")
    def test_network_error(self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError(
            "Network unreachable"
        )

        client = get_api_client(self.env, "test_stripe")

        with self.assertRaises(CommError) as context:
            client.get("/test")

        self.assertIn("Network", str(context.exception))

    @patch("requests.Session.request")
    def test_timeout_error(self, mock_request):
        mock_request.side_effect = requests.exceptions.Timeout("Request timeout")

        client = get_api_client(self.env, "test_stripe")

        with self.assertRaises(CommError) as context:
            client.get("/test")

        self.assertIn("timed out", str(context.exception).lower())


@tagged("post_install", "-at_install", "integration")
class TestAPIClientLogging(APITransportTestCase):
    @patch("requests.Session.request")
    def test_successful_request_logging(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_stripe")

        log_count_before = self.env["integration.exchange"].search_count([])

        client.get("/test")

        self.flush_pending_logs()

        log_count_after = self.env["integration.exchange"].search_count([])

        self.assertEqual(log_count_after, log_count_before + 1)

        channel_ref = f"integration.service,{self.service_stripe.id}"
        log = self.env["integration.exchange"].search(
            [("channel_id", "=", channel_ref)],
            order="timestamp desc",
            limit=1,
        )

        self.assertTrue(log.exists())
        self.assertEqual(log.request_method, "GET")
        self.assertEqual(log.status_code, 200)
        self.assertTrue(log.is_success)

    @patch("requests.Session.request")
    def test_failed_request_logging(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=500, json_data={"error": "Server error"}
        )

        client = get_api_client(self.env, "test_stripe")

        with contextlib.suppress(CommError):
            client.get("/test")

        self.flush_pending_logs()

        log = self.env["integration.exchange"].search(
            [],
            order="timestamp desc",
            limit=1,
        )

        self.assertEqual(log.status_code, 500)
        self.assertFalse(log.is_success)
        self.assertEqual(log.status_category, "server_error")

    @patch("requests.Session.request")
    def test_response_time_logging(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_stripe")
        client.get("/test")

        self.flush_pending_logs()

        log = self.env["integration.exchange"].search(
            [],
            order="timestamp desc",
            limit=1,
        )

        self.assertIsNotNone(log.duration_ms)
        self.assertGreaterEqual(log.duration_ms, 0)
        self.assertIsNotNone(log.performance_rating)


@tagged("post_install", "-at_install", "integration")
class TestAPIClientHeaders(APITransportTestCase):
    @patch("requests.Session.request")
    def test_custom_headers(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_stripe")
        custom_headers = {
            "X-Custom-Header": "custom-value",
            "X-Request-ID": "123",
        }

        client.get("/test", headers=custom_headers)

        call_kwargs = mock_request.call_args[1]
        headers = call_kwargs.get("headers", {})

        self.assertIn("X-Custom-Header", headers)
        self.assertEqual(headers["X-Custom-Header"], "custom-value")
        self.assertIn("X-Request-ID", headers)
        self.assertEqual(headers["X-Request-ID"], "123")

    @patch("requests.Session.request")
    def test_default_headers(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_stripe")
        client.get("/test")

        self.assertIn("User-Agent", client.session.headers)
        self.assertIn("Odoo", client.session.headers["User-Agent"])
