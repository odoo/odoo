from contextlib import nullcontext
from unittest.mock import patch

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSecretUseCounter(TransactionCase):
    def setUp(self):
        super().setUp()
        self.credential = self.env["credential.credential"].create(
            {
                "name": "counted",
                "category_id": self.env.ref(
                    "credential.credential_category_api_key"
                ).id,
                "api_key": "K",
            }
        )

    def _flush_into_this_transaction(self, callbacks):
        with patch.object(
            self.env.registry, "cursor", lambda: nullcontext(self.env.cr)
        ):
            callbacks.run()

    def _counts(self):
        return {
            use.purpose: use.use_count
            for use in self.env["credential.use"].search(
                [("credential_id", "=", self.credential.id)]
            )
        }

    def test_a_use_needs_a_purpose(self):
        for purpose in ("", "Bearer", "has space", "x" * 65, None):
            with self.subTest(purpose=purpose), self.assertRaises(ValueError):
                self.credential._use_secret(purpose)

    def test_uses_are_counted_per_purpose_and_day_after_the_commit(self):
        for _ in range(3):
            self.credential._use_secret("integration:api_key")
        self.credential._use_secret_payload("env:claude_sdk")
        self.assertEqual(self._counts(), {}, "nothing is written before the commit")

        self._flush_into_this_transaction(self.env.cr.postcommit)
        self.env.invalidate_all()

        self.assertEqual(
            self._counts(), {"integration:api_key": 3, "env:claude_sdk": 1}
        )
        row = self.env["credential.use"].search(
            [("credential_id", "=", self.credential.id)], limit=1
        )
        self.assertEqual(row.day, fields.Date.today())
        self.assertEqual(row.company_id, self.credential.company_id)

    def test_a_later_transaction_adds_to_the_same_row(self):
        self.credential._use_secret("integration:api_key")
        self._flush_into_this_transaction(self.env.cr.postcommit)
        self.credential._use_secret("integration:api_key")
        self._flush_into_this_transaction(self.env.cr.postcommit)
        self.env.invalidate_all()
        self.assertEqual(self._counts(), {"integration:api_key": 2})

    def test_a_rolled_back_transaction_still_counts_its_uses(self):
        self.credential._use_basic_auth("delivery:carrier")
        self.env.cr.postcommit.clear()
        self._flush_into_this_transaction(self.env.cr.postrollback)
        self.env.invalidate_all()
        self.assertEqual(self._counts(), {"delivery:carrier": 1})

    def test_use_writes_no_reveal_audit_row(self):
        self.credential._use_secret("integration:api_key")
        self._flush_into_this_transaction(self.env.cr.postcommit)
        self.assertFalse(
            self.env["credential.access.log"].search_count(
                [("credential_id", "=", self.credential.id), ("operation", "=", "read")]
            )
        )
