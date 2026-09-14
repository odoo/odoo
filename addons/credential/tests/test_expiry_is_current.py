from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import TransactionCase


class TestExpiryIsCurrent(TransactionCase):
    def _credential(self, name, date_expiration):
        return self.env["credential.credential"].create(
            {
                "name": name,
                "category_id": self.env.ref(
                    "credential.credential_category_api_key"
                ).id,
                "credential_value": "s3cr3t",
                "date_expiration": date_expiration,
            }
        )

    def test_a_credential_expires_when_its_date_passes_not_when_it_is_written(self):
        now = fields.Datetime.now()
        credential = self._credential("tomorrow", now + timedelta(days=1))
        self.assertFalse(credential.is_expired)
        self.env.flush_all()

        with freeze_time(now + timedelta(days=2)):
            self.env.invalidate_all()
            self.assertTrue(credential.is_expired)
            self.assertIn(
                credential,
                self.env["credential.credential"].search([("is_expired", "=", True)]),
            )

    def test_a_credential_without_a_date_never_expires(self):
        credential = self._credential("forever", False)
        Credential = self.env["credential.credential"]
        self.assertFalse(credential.is_expired)
        self.assertIn(credential, Credential.search([("is_expired", "=", False)]))
        self.assertNotIn(credential, Credential.search([("is_expired", "=", True)]))
        self.assertIn(credential, Credential.search([("is_expired", "!=", True)]))
