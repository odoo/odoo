from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestResponseCacheGc(TransactionCase):
    def setUp(self):
        super().setUp()
        self.service = self.env["integration.service"].create(
            {
                "name": "GC Probe",
                "code": "gc_probe",
                "endpoint_url": "https://example.invalid",
                "cache_enabled": True,
            }
        )
        self.model = self.env["integration.response.cache"]
        self.model.search([]).unlink()

    def _entry(self, index):
        return self.model.create(
            {
                "cache_key": f"gc-probe-{index}",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "request_url": f"/probe/{index}",
                "response_body": {"index": index},
                "status_code": 200,
                "date_expiration": fields.Datetime.add(fields.Datetime.now(), hours=1),
                "ttl_seconds": 3600,
            }
        )

    def test_lru_eviction_uses_unflushed_hit_counts(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "integration.max_cache_entries", "5"
        )
        entries = self.model
        for i in range(10):
            entries |= self._entry(i)
        self.env.flush_all()
        self.env.invalidate_all()

        for i, entry in enumerate(entries):
            entry.hit_count = i

        self.model._gc_least_used_cache()

        remaining = self.model.search([])
        self.assertEqual(len(remaining), 5)
        self.assertEqual(
            sorted(remaining.mapped("hit_count")),
            [5, 6, 7, 8, 9],
            "eviction must drop the five genuinely least-used entries, not "
            "whichever five were stalest in Postgres",
        )

    def test_expired_eviction_sees_unflushed_expiry(self):
        keep = self._entry(1)
        drop = self._entry(2)
        self.env.flush_all()

        drop.date_expiration = fields.Datetime.subtract(fields.Datetime.now(), hours=1)
        self.model._gc_expired_cache()

        self.assertTrue(keep.exists())
        self.assertFalse(drop.exists())

    def test_collected_rows_leave_the_orm_cache(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "integration.max_cache_entries", "1"
        )
        entries = self.model
        for i in range(4):
            entries |= self._entry(i)
        for i, entry in enumerate(entries):
            entry.hit_count = i

        self.model._gc_least_used_cache()
        self.assertEqual(len(entries.exists()), 1)
