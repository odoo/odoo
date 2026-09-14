import json
from datetime import timedelta
from unittest.mock import Mock

import requests

from odoo import fields
from odoo.tests.common import TransactionCase


class APITransportTestCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.cat_custom = cls.env.ref("credential.credential_category_custom")

        cls.company_a = cls.env["res.company"].create(
            {
                "name": "Test Company A",
            },
        )
        cls.company_b = cls.env["res.company"].create(
            {
                "name": "Test Company B",
            },
        )

        cls.service_stripe = cls.env["integration.service"].create(
            {
                "name": "Stripe Test",
                "code": "test_stripe",
                "category": "payment",
                "endpoint_url": "https://api.stripe.com/v1",
                "endpoint_url_test": "https://api.stripe.test/v1",
                "environment": "test",
                "company_id": cls.env.company.id,
            },
        )

        cls.service_with_auth = cls.env["integration.service"].create(
            {
                "name": "Authenticated API",
                "code": "test_auth_api",
                "category": "other",
                "endpoint_url": "https://api.example.com",
                "environment": "production",
                "company_id": cls.env.company.id,
                "auth_type": "bearer",
            },
        )

        cls.service_basic_auth = cls.env["integration.service"].create(
            {
                "name": "Basic Auth API",
                "code": "test_basic_auth",
                "category": "other",
                "endpoint_url": "https://api.basic.com",
                "environment": "production",
                "company_id": cls.env.company.id,
                "auth_type": "basic",
            },
        )

        cls.service_with_rate_limit = cls.env["integration.service"].create(
            {
                "name": "Rate Limited API",
                "code": "test_rate_limit",
                "category": "other",
                "endpoint_url": "https://api.ratelimit.com",
                "environment": "production",
                "company_id": cls.env.company.id,
                "rate_limit_enabled": True,
                "rate_limit_requests": 10,
                "rate_limit_period": "minute",
            },
        )

        cls.service_with_cache = cls.env["integration.service"].create(
            {
                "name": "Cached API",
                "code": "test_cache",
                "category": "other",
                "endpoint_url": "https://api.cache.com",
                "environment": "production",
                "company_id": cls.env.company.id,
                "cache_enabled": True,
                "cache_ttl": 300,
            },
        )

        cls.credential_stripe = cls.env["credential.credential"].create(
            {
                "name": "Stripe Test Credential",
                "endpoint_id": cls.service_stripe.id,
                "company_id": cls.env.company.id,
                "category_id": cls.cat_custom.id,
                "environment": "test",
                "credential_value": "sk_test_123456789",
            },
        )

        cls.credential_bearer = cls.env["credential.credential"].create(
            {
                "name": "Bearer Token Credential",
                "endpoint_id": cls.service_with_auth.id,
                "company_id": cls.env.company.id,
                "category_id": cls.cat_custom.id,
                "environment": "production",
                "bearer_token": "bearer_token_xyz",
            },
        )

        cls.credential_basic = cls.env["credential.credential"].create(
            {
                "name": "Basic Auth Credential",
                "endpoint_id": cls.service_basic_auth.id,
                "company_id": cls.env.company.id,
                "category_id": cls.cat_custom.id,
                "environment": "production",
                "username": "testuser",
                "password": "testpass123",
            },
        )

        cls.credential_api_key = cls.env["credential.credential"].create(
            {
                "name": "API Key Credential",
                "endpoint_id": cls.service_with_cache.id,
                "company_id": cls.env.company.id,
                "category_id": cls.cat_custom.id,
                "environment": "production",
                "credential_value": "api_key_abc123",
            },
        )

        cls.credential_rate_limit = cls.env["credential.credential"].create(
            {
                "name": "Rate Limit Credential",
                "endpoint_id": cls.service_with_rate_limit.id,
                "company_id": cls.env.company.id,
                "category_id": cls.cat_custom.id,
                "environment": "production",
                "credential_value": "rate_limit_token",
            },
        )

    def create_mock_response(
        self,
        status_code=200,
        json_data=None,
        text=None,
        headers=None,
    ):
        mock_response = Mock(headers={"content-type": "application/json"})
        mock_response.status_code = status_code
        mock_response.headers = headers or {}

        if json_data is not None:
            mock_response.json.return_value = json_data
            mock_response.text = json.dumps(json_data)
        else:
            mock_response.text = text or ""
            mock_response.json.side_effect = ValueError("No JSON")

        if 400 <= status_code < 600:
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response,
            )
        else:
            mock_response.raise_for_status.return_value = None

        return mock_response

    def create_request_log(
        self,
        service=None,
        method="GET",
        url=None,
        status_code=200,
        response_time=100.0,
        cache_hit=False,
        timestamp=None,
    ):
        service = service or self.service_stripe
        url = url or f"{service.endpoint_url}/test"
        timestamp = timestamp or fields.Datetime.now()

        channel_ref = f"integration.service,{service.id}"
        return self.env["integration.exchange"].create(
            {
                "direction": "outbound",
                "channel_id": channel_ref,
                "credential_id": self.credential_stripe.id,
                "company_id": self.env.company.id,
                "user_id": self.env.user.id,
                "request_method": method.upper(),
                "request_url": url,
                "status_code": status_code,
                "timestamp": timestamp,
                "date_completed": timestamp + timedelta(milliseconds=response_time),
                "duration_ms": response_time,
                "cache_hit": cache_hit,
            },
        )

    def create_cache_entry(
        self,
        service=None,
        url=None,
        response_body=None,
        ttl=300,
        expired=False,
    ):
        service = service or self.service_with_cache
        url = url or "/test/endpoint"
        response_body = response_body or {"data": "test"}

        if expired:
            date_created = fields.Datetime.now() - timedelta(seconds=ttl + 10)
            date_expiration = date_created + timedelta(seconds=ttl)
        else:
            date_created = fields.Datetime.now()
            date_expiration = date_created + timedelta(seconds=ttl)

        cache_key = self.env["integration.response.cache"]._generate_cache_key(
            service.code,
            url,
            None,
        )

        return self.env["integration.response.cache"].create(
            {
                "cache_key": cache_key,
                "endpoint_id": service.id,
                "company_id": self.env.company.id,
                "request_url": url,
                "response_body": response_body,
                "status_code": 200,
                "date_created": date_created,
                "date_expiration": date_expiration,
                "ttl_seconds": ttl,
            },
        )

    def assertValidResponse(self, response):  # pylint: disable=invalid-name
        self.assertIsInstance(response, dict)
        self.assertIn("status_code", response)
        self.assertIn("body", response)
        self.assertIn("headers", response)

    def assertSuccessResponse(self, response):  # pylint: disable=invalid-name
        self.assertValidResponse(response)
        self.assertTrue(
            200 <= response["status_code"] < 300,
            f"Expected success status code, got {response['status_code']}",
        )

    def assertCacheHit(self, response):  # pylint: disable=invalid-name
        self.assertValidResponse(response)
        self.assertTrue(
            response.get("from_cache", False),
            "Expected response from cache",
        )

    def assertCacheMiss(self, response):  # pylint: disable=invalid-name
        self.assertValidResponse(response)
        self.assertFalse(
            response.get("from_cache", False),
            "Expected response not from cache",
        )

    def flush_pending_logs(self):
        self.env.cr.precommit.run()
