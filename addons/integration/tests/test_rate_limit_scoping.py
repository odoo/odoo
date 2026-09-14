from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.integration.tools import get_api_client
from odoo.addons.integration.tools.exceptions import RateLimitError


@tagged("post_install", "-at_install")
class TestRateLimitScoping(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env["res.company"].create({"name": "Scope A"})
        cls.company_b = cls.env["res.company"].create({"name": "Scope B"})

    def _endpoint(self, code, requests_allowed=2):
        return self.env["integration.service"].create(
            {
                "name": code,
                "code": code,
                "endpoint_url": "https://example.invalid/api",
                "auth_type": "none",
                "rate_limit_enabled": True,
                "rate_limit_requests": requests_allowed,
                "rate_limit_period": "hour",
            }
        )

    @mute_logger("odoo.addons.rate_limit.tools.endpoint_rate_limiter")
    def test_a_company_scoped_bucket_is_not_shared(self):
        endpoint = self._endpoint("scoped")

        self.assertTrue(endpoint.check_rate_limit(company_id=self.company_a.id))
        self.assertTrue(endpoint.check_rate_limit(company_id=self.company_a.id))
        self.assertFalse(
            endpoint.check_rate_limit(company_id=self.company_a.id),
            "company A must run out after its own two",
        )

        self.assertTrue(
            endpoint.check_rate_limit(company_id=self.company_b.id),
            "company B has its own allowance and A's exhaustion is not its problem",
        )

    @mute_logger("odoo.addons.rate_limit.tools.endpoint_rate_limiter")
    def test_an_unscoped_bucket_is_shared(self):
        endpoint = self._endpoint("unscoped")

        self.assertTrue(endpoint.check_rate_limit())
        self.assertTrue(endpoint.check_rate_limit())
        self.assertFalse(endpoint.check_rate_limit())

    @mute_logger("odoo.addons.rate_limit.tools.endpoint_rate_limiter")
    def test_the_two_scopes_are_different_buckets(self):
        endpoint = self._endpoint("both")
        buckets = self.env["rate.limit.bucket"].sudo()

        endpoint.check_rate_limit()
        endpoint.check_rate_limit(company_id=self.company_a.id)

        keys = buckets.search(
            [
                ("endpoint_model", "=", "integration.service"),
                ("endpoint_id", "=", endpoint.id),
            ]
        ).mapped("bucket_key")
        self.assertIn(f"integration.service:{endpoint.id}:global", keys)
        self.assertIn(f"integration.service:{endpoint.id}:{self.company_a.id}", keys)

    def test_disabled_means_allowed_without_touching_a_bucket(self):
        endpoint = self._endpoint("disabled")
        endpoint.rate_limit_enabled = False
        buckets = self.env["rate.limit.bucket"].sudo()

        for _ in range(5):
            self.assertTrue(endpoint.check_rate_limit(company_id=self.company_a.id))

        self.assertFalse(
            buckets.search(
                [
                    ("endpoint_model", "=", "integration.service"),
                    ("endpoint_id", "=", endpoint.id),
                ]
            ),
            "a disabled limit must not leave rows for the collector to clean",
        )

    @mute_logger("odoo.addons.rate_limit.tools.endpoint_rate_limiter")
    def test_the_outbound_client_spends_its_own_company_s_allowance(self):
        endpoint = self._endpoint("client_scope")
        self.env["credential.credential"].create(
            {
                "name": "client scope cred",
                "endpoint_id": endpoint.id,
                "company_id": self.company_a.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
            }
        )
        client = get_api_client(self.env, endpoint.code, company_id=self.company_a.id)

        client.check_rate_limit()
        client.check_rate_limit()
        with self.assertRaises(RateLimitError):
            client.check_rate_limit()

        buckets = (
            self.env["rate.limit.bucket"]
            .sudo()
            .search(
                [
                    ("endpoint_model", "=", "integration.service"),
                    ("endpoint_id", "=", endpoint.id),
                ]
            )
        )
        self.assertEqual(
            buckets.mapped("bucket_key"),
            [f"integration.service:{endpoint.id}:{self.company_a.id}"],
            "the client spent a company-scoped bucket, and only that one",
        )
