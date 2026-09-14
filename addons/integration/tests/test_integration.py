from datetime import timedelta
from unittest.mock import patch

import requests

from odoo import fields
from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import get_api_client
from odoo.addons.integration.tools.exceptions import (
    CommError,
    RateLimitError,
)


@tagged("post_install", "-at_install", "integration")
class TestIntegration(APITransportTestCase):
    @patch("requests.Session.request")
    def test_complete_api_request_flow(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200,
            json_data={"id": 123, "name": "Test Customer"},
            headers={"Content-Type": "application/json"},
        )

        client = get_api_client(self.env, "test_cache")

        self.assertIsNotNone(client)
        self.assertEqual(client.endpoint_code, "test_cache")

        response1 = client.get("/customers/123")

        self.assertEqual(response1["status_code"], 200)
        self.assertEqual(response1["body"]["id"], 123)
        self.assertFalse(response1.get("from_cache", False))

        self.flush_pending_logs()
        log = self.env["integration.exchange"].search(
            [
                (
                    "channel_id",
                    "=",
                    f"integration.service,{self.service_with_cache.id}",
                )
            ],
            order="timestamp desc",
            limit=1,
        )

        self.assertTrue(log.exists())
        self.assertEqual(log.request_method, "GET")
        self.assertIn("/customers/123", log.request_url)
        self.assertEqual(log.status_code, 200)
        self.assertTrue(log.is_success)

        mock_request.reset_mock()
        response2 = client.get("/customers/123")

        self.assertEqual(response2["status_code"], 200)
        self.assertEqual(response2["body"]["id"], 123)
        self.assertTrue(response2.get("from_cache", False))

        self.assertFalse(mock_request.called)

    @patch("requests.Session.request")
    def test_authentication_and_headers_flow(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"authenticated": True}
        )

        client = get_api_client(self.env, "test_auth_api")

        client.get("/protected", headers={"X-Custom": "value", "X-Request-ID": "123"})

        call_kwargs = mock_request.call_args[1]
        headers = call_kwargs.get("headers", {})

        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Bearer "))

        self.assertEqual(headers["X-Custom"], "value")
        self.assertEqual(headers["X-Request-ID"], "123")

        self.assertIn("User-Agent", client.session.headers)

    @patch("requests.Session.request")
    def test_error_handling_and_logging_flow(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=500,
            json_data={"error": "Internal Server Error"},
        )

        client = get_api_client(self.env, "test_stripe")

        with self.assertRaises(CommError):
            client.get("/fail")

        self.flush_pending_logs()
        log = self.env["integration.exchange"].search(
            [
                (
                    "channel_id",
                    "=",
                    f"integration.service,{self.service_stripe.id}",
                )
            ],
            order="timestamp desc",
            limit=1,
        )

        self.assertTrue(log.exists())
        self.assertEqual(log.status_code, 500)
        self.assertFalse(log.is_success)
        self.assertEqual(log.status_category, "server_error")
        self.assertIsNotNone(log.error_message)

    @patch("requests.Session.request")
    def test_rate_limiting_enforcement_flow(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_rate_limit")

        for i in range(10):
            response = client.get(f"/test/{i}")
            self.assertEqual(response["status_code"], 200)

        with self.assertRaises(RateLimitError):
            client.get("/test/11")

        self.flush_pending_logs()
        logs = self.env["integration.exchange"].search(
            [
                (
                    "channel_id",
                    "=",
                    f"integration.service,{self.service_with_rate_limit.id}",
                ),
                ("is_success", "=", True),
            ]
        )

        self.assertGreaterEqual(len(logs), 10)

    @patch("requests.Session.request")
    def test_multicompany_isolation_flow(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        self.env["credential.credential"].create(
            {
                "name": "Company A Credential",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.company_a.id,
                "category_id": self.cat_custom.id,
                "environment": "test",
                "credential_value": "token_company_a",
            }
        )

        self.env["credential.credential"].create(
            {
                "name": "Company B Credential",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.company_b.id,
                "category_id": self.cat_custom.id,
                "environment": "test",
                "credential_value": "token_company_b",
            }
        )

        client_a = get_api_client(self.env, "test_stripe", company_id=self.company_a.id)
        client_a.get("/test/a")

        client_b = get_api_client(self.env, "test_stripe", company_id=self.company_b.id)
        client_b.get("/test/b")

        self.flush_pending_logs()
        channel_ref = f"integration.service,{self.service_stripe.id}"
        logs_a = self.env["integration.exchange"].search(
            [
                ("channel_id", "=", channel_ref),
                ("company_id", "=", self.company_a.id),
            ]
        )

        logs_b = self.env["integration.exchange"].search(
            [
                ("channel_id", "=", channel_ref),
                ("company_id", "=", self.company_b.id),
            ]
        )

        self.assertGreater(len(logs_a), 0)
        self.assertGreater(len(logs_b), 0)

        log_ids_a = set(logs_a.ids)
        log_ids_b = set(logs_b.ids)
        self.assertEqual(len(log_ids_a & log_ids_b), 0)

    @patch("requests.Session.request")
    def test_credential_encryption_integration(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"success": True}
        )

        credential = self.env["credential.credential"].create(
            {
                "name": "Encrypted Credential",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.env.company.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "api_key": "sensitive_api_key_12345",
                "api_secret": "sensitive_secret_67890",
            }
        )

        self.assertIsNotNone(credential.credential_value_encrypted)

        credential.invalidate_recordset(
            ["cached_plaintext", "credential_data", "api_key", "api_secret"]
        )

        self.assertEqual(credential.api_key, "sensitive_api_key_12345")
        self.assertEqual(credential.api_secret, "sensitive_secret_67890")

        access_logs = self.env["credential.access.log"].search(
            [("credential_id", "=", credential.id)]
        )

        self.assertGreater(len(access_logs), 0)

        view_logs = access_logs.filtered(lambda log: log.operation == "read")
        self.assertGreater(len(view_logs), 0)

    @patch("requests.Session.request")
    def test_cache_expiration_workflow(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "original", "timestamp": 1}
        )

        client = get_api_client(self.env, "test_cache")

        response1 = client.get("/test/expiring")
        self.assertEqual(response1["body"]["data"], "original")
        self.assertFalse(response1.get("from_cache", False))

        mock_request.reset_mock()
        response2 = client.get("/test/expiring")
        self.assertEqual(response2["body"]["data"], "original")
        self.assertTrue(response2.get("from_cache", False))

        cache = self.env["integration.response.cache"].search(
            [
                ("endpoint_id", "=", self.service_with_cache.id),
                ("request_url", "ilike", "%/test/expiring%"),
            ],
            limit=1,
        )

        if cache:
            cache.write(
                {"date_expiration": fields.Datetime.now() - timedelta(seconds=10)}
            )

        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "refreshed", "timestamp": 2}
        )

        response3 = client.get("/test/expiring")
        self.assertEqual(response3["body"]["data"], "refreshed")
        self.assertFalse(response3.get("from_cache", False))

        self.assertTrue(mock_request.called)

    @patch("requests.Session.request")
    def test_post_request_with_data(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=201, json_data={"id": 999, "created": True}
        )

        client = get_api_client(self.env, "test_stripe")

        response = client.post(
            "/customers",
            json={
                "email": "customer@example.com",
                "name": "Test Customer",
                "metadata": {"source": "odoo"},
            },
        )

        self.assertEqual(response["status_code"], 201)
        self.assertEqual(response["body"]["id"], 999)
        self.assertTrue(response["body"]["created"])

        call_kwargs = mock_request.call_args[1]
        self.assertEqual(call_kwargs["json"]["email"], "customer@example.com")
        self.assertEqual(call_kwargs["json"]["name"], "Test Customer")

        self.flush_pending_logs()
        log = self.env["integration.exchange"].search(
            [
                (
                    "channel_id",
                    "=",
                    f"integration.service,{self.service_stripe.id}",
                )
            ],
            order="timestamp desc",
            limit=1,
        )

        self.assertEqual(log.request_method, "POST")
        self.assertEqual(log.status_code, 201)

    @patch("requests.Session.request")
    def test_retry_on_network_error(self, mock_request):
        mock_request.side_effect = [
            requests.exceptions.ConnectionError("Network error"),
            self.create_mock_response(status_code=200, json_data={"data": "success"}),
        ]

        client = get_api_client(self.env, "test_stripe")

        with self.assertRaises(CommError):
            client.get("/test")

    @patch("requests.Session.request")
    def test_health_check_integration(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"status": "healthy"}
        )

        self.service_stripe.health_check_environment = "test"

        self.service_stripe.action_check_health()

        self.assertTrue(self.service_stripe.is_healthy)
        self.assertIsNotNone(self.service_stripe.last_health_check)

        self.flush_pending_logs()
        log = self.env["integration.exchange"].search(
            [
                (
                    "channel_id",
                    "=",
                    f"integration.service,{self.service_stripe.id}",
                )
            ],
            order="timestamp desc",
            limit=1,
        )

        self.assertTrue(log.exists())
        self.assertEqual(log.status_code, 200)
