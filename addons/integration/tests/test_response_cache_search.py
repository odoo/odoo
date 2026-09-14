from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestResponseCacheExpirySearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["integration.service"].create(
            {
                "name": "Expiry Probe",
                "code": "expiry_probe",
                "endpoint_url": "https://example.invalid",
                "cache_enabled": True,
            }
        )
        cls.fresh = cls._entry("fresh", 1)
        cls.stale = cls._entry("stale", -1)

    @classmethod
    def _entry(cls, key, hours):
        return cls.env["integration.response.cache"].create(
            {
                "cache_key": f"expiry-{key}",
                "endpoint_id": cls.service.id,
                "company_id": cls.env.company.id,
                "request_url": f"/probe/{key}",
                "response_body": {"key": key},
                "status_code": 200,
                "date_expiration": fields.Datetime.add(
                    fields.Datetime.now(), hours=hours
                ),
                "ttl_seconds": 3600,
            }
        )

    def _search(self, domain):
        scope = [("id", "in", (self.fresh | self.stale).ids)]
        return self.env["integration.response.cache"].search(scope + domain)

    def test_the_expired_entries_can_be_listed(self):
        for domain in (
            [("is_expired", "=", True)],
            [("is_expired", "!=", False)],
            [("is_expired", "in", [True])],
        ):
            with self.subTest(domain=domain):
                self.assertEqual(self._search(domain), self.stale)

    def test_the_live_entries_can_be_listed(self):
        for domain in (
            [("is_expired", "=", False)],
            [("is_expired", "!=", True)],
            [("is_expired", "not in", [True])],
        ):
            with self.subTest(domain=domain):
                self.assertEqual(self._search(domain), self.fresh)
