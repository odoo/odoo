from unittest.mock import patch

from psycopg import errors as psycopg_errors

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGetOrCreateBucket(TransactionCase):
    def test_creates_then_reuses_global_bucket(self):
        Bucket = self.env["rate.limit.bucket"]
        endpoint = self.env["res.partner"].create({"name": "Endpoint"})
        bucket = Bucket.get_or_create_bucket(endpoint, company_id=None)
        self.assertTrue(bucket)
        self.assertEqual(bucket.bucket_key, f"res.partner:{endpoint.id}:global")
        self.assertEqual(bucket.tokens, 100.0)
        again = Bucket.get_or_create_bucket(endpoint, company_id=None)
        self.assertEqual(again, bucket)

    def test_company_scoped_bucket_key(self):
        Bucket = self.env["rate.limit.bucket"]
        endpoint = self.env["res.partner"].create({"name": "Endpoint2"})
        bucket = Bucket.get_or_create_bucket(endpoint, company_id=self.env.company.id)
        self.assertEqual(
            bucket.bucket_key,
            f"res.partner:{endpoint.id}:{self.env.company.id}",
        )

    def test_race_falls_back_to_existing_row_on_unique_violation(self):
        Bucket = self.env["rate.limit.bucket"]
        endpoint = self.env["res.partner"].create({"name": "Race endpoint"})
        existing = Bucket.get_or_create_bucket(endpoint, company_id=None)

        with (
            patch.object(
                type(Bucket), "search", side_effect=[Bucket.browse(), existing]
            ),
            patch.object(
                type(Bucket), "create", side_effect=psycopg_errors.UniqueViolation()
            ),
        ):
            bucket = Bucket.get_or_create_bucket(endpoint, company_id=None)

        self.assertEqual(bucket, existing)
