from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import get_api_client
from odoo.addons.integration.tools.exceptions import CommError


@tagged("post_install", "-at_install", "integration")
class TestMultiCompany(APITransportTestCase):
    def test_credentials_isolated_by_company(self):
        credential_a = self.env["credential.credential"].create(
            {
                "name": "Company A Credential",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.company_a.id,
                "category_id": self.cat_custom.id,
                "environment": "test",
                "credential_value": "token_company_a",
            }
        )

        credential_b = self.env["credential.credential"].create(
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

        self.assertEqual(client_a.credential.id, credential_a.id)
        self.assertEqual(client_a.credential.company_id.id, self.company_a.id)

        client_b = get_api_client(self.env, "test_stripe", company_id=self.company_b.id)

        self.assertEqual(client_b.credential.id, credential_b.id)
        self.assertEqual(client_b.credential.company_id.id, self.company_b.id)

        self.assertNotEqual(client_a.credential.id, client_b.credential.id)

    def test_logs_isolated_by_company(self):
        log_default = self.create_request_log(
            service=self.service_stripe,
            url="/test/default",
        )
        log_default.company_id = self.env.company

        log_a = self.create_request_log(
            service=self.service_stripe,
            url="/test/company_a",
        )
        log_a.company_id = self.company_a

        log_b = self.create_request_log(
            service=self.service_stripe,
            url="/test/company_b",
        )
        log_b.company_id = self.company_b

        channel_ref = f"integration.service,{self.service_stripe.id}"
        logs_default = self.env["integration.exchange"].search(
            [
                ("channel_id", "=", channel_ref),
                ("company_id", "=", self.env.company.id),
            ]
        )

        self.assertIn(log_default.id, logs_default.ids)
        self.assertNotIn(log_a.id, logs_default.ids)
        self.assertNotIn(log_b.id, logs_default.ids)

        logs_a = self.env["integration.exchange"].search(
            [
                ("channel_id", "=", channel_ref),
                ("company_id", "=", self.company_a.id),
            ]
        )

        self.assertIn(log_a.id, logs_a.ids)
        self.assertNotIn(log_default.id, logs_a.ids)
        self.assertNotIn(log_b.id, logs_a.ids)

    def test_cache_isolated_by_company(self):
        cache_default = self.create_cache_entry(
            service=self.service_with_cache,
            url="/test/default",
            response_body={"company": "default"},
        )
        cache_default.company_id = self.env.company

        cache_key_a = self.env["integration.response.cache"]._generate_cache_key(
            "test_cache", "/test/company_a", None
        )
        now = fields.Datetime.now()
        self.env["integration.response.cache"].create(
            {
                "cache_key": cache_key_a,
                "endpoint_id": self.service_with_cache.id,
                "company_id": self.company_a.id,
                "request_url": "/test/company_a",
                "response_body": {"company": "a"},
                "date_created": now,
                "date_expiration": now + timedelta(seconds=300),
                "ttl_seconds": 300,
            }
        )

        cached_default = self.env["integration.response.cache"].get_cached_response(
            endpoint_code="test_cache",
            url="/test/default",
            company_id=self.env.company.id,
        )

        self.assertIsNotNone(cached_default)
        self.assertEqual(cached_default["body"]["company"], "default")

        cached_a = self.env["integration.response.cache"].get_cached_response(
            endpoint_code="test_cache",
            url="/test/company_a",
            company_id=self.company_a.id,
        )

        self.assertIsNotNone(cached_a)
        self.assertEqual(cached_a["body"]["company"], "a")

        cached_cross = self.env["integration.response.cache"].get_cached_response(
            endpoint_code="test_cache",
            url="/test/default",
            company_id=self.company_a.id,
        )

        self.assertIsNone(cached_cross)

    def test_service_availability_per_company(self):
        service_a = self.env["integration.service"].create(
            {
                "name": "Company A Service",
                "code": "test_company_a_service",
                "category": "other",
                "endpoint_url": "https://api.company-a.com",
                "environment": "production",
                "company_id": self.company_a.id,
            }
        )

        self.env["credential.credential"].create(
            {
                "name": "Company A Service Credential",
                "endpoint_id": service_a.id,
                "company_id": self.company_a.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "credential_value": "token_a",
            }
        )

        client_a = get_api_client(
            self.env, "test_company_a_service", company_id=self.company_a.id
        )
        self.assertIsNotNone(client_a)

        with self.assertRaises(CommError) as context:
            get_api_client(
                self.env, "test_company_a_service", company_id=self.company_b.id
            )

        self.assertIn("No active credentials", str(context.exception))

    def test_credential_access_log_company_isolation(self):
        credential_a = self.env["credential.credential"].create(
            {
                "name": "Company A Credential",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.company_a.id,
                "category_id": self.cat_custom.id,
                "environment": "test",
                "api_key": "key_company_a",
            }
        )

        credential_b = self.env["credential.credential"].create(
            {
                "name": "Company B Credential",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.company_b.id,
                "category_id": self.cat_custom.id,
                "environment": "test",
                "api_key": "key_company_b",
            }
        )

        _ = credential_a.api_key
        _ = credential_b.api_key

        logs_a = self.env["credential.access.log"].search(
            [("credential_id.company_id", "=", self.company_a.id)]
        )

        self.assertGreater(len(logs_a), 0)

        for log in logs_a:
            self.assertEqual(log.credential_id.company_id.id, self.company_a.id)

        logs_b = self.env["credential.access.log"].search(
            [("credential_id.company_id", "=", self.company_b.id)]
        )

        self.assertGreater(len(logs_b), 0)

        for log in logs_b:
            self.assertEqual(log.credential_id.company_id.id, self.company_b.id)

        log_ids_a = set(logs_a.ids)
        log_ids_b = set(logs_b.ids)
        self.assertEqual(len(log_ids_a & log_ids_b), 0)
