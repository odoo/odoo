from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestExpiryWarning(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env.ref("credential.credential_category_api_key")

    def _credential(self, name, expires_in_days=None, **vals):
        values = {
            "name": name,
            "category_id": self.category.id,
            "credential_value": "s3cr3t",
            **vals,
        }
        if expires_in_days is not None:
            values["date_expiration"] = fields.Datetime.now() + timedelta(
                days=expires_in_days
            )
        return self.env["credential.credential"].create(values)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_credential_without_an_endpoint_is_warned(self):
        credential = self._credential("vault-only", expires_in_days=10)

        result = self.env["credential.credential"].cron_check_expiring_credentials()

        self.assertEqual(result["warned"], 1)
        self.assertTrue(credential.date_expiry_warned)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_a_credential_is_named_once_not_every_pass(self):
        credential = self._credential("warn-once", expires_in_days=10)
        Credential = self.env["credential.credential"]

        first = Credential.cron_check_expiring_credentials()
        stamp = credential.date_expiry_warned
        second = Credential.cron_check_expiring_credentials()

        self.assertEqual(first["warned"], 1)
        self.assertEqual(second["warned"], 0)
        self.assertEqual(credential.date_expiry_warned, stamp)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_renewing_the_date_re_arms_the_warning(self):
        credential = self._credential("renewed", expires_in_days=10)
        Credential = self.env["credential.credential"]
        Credential.cron_check_expiring_credentials()
        self.assertTrue(credential.date_expiry_warned)

        credential.write(
            {"date_expiration": fields.Datetime.now() + timedelta(days=20)}
        )

        self.assertFalse(credential.date_expiry_warned)
        self.assertEqual(Credential.cron_check_expiring_credentials()["warned"], 1)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_outside_the_window_and_already_expired_are_both_ignored(self):
        self._credential("far-future", expires_in_days=90)
        self._credential("already-expired", expires_in_days=-1)
        self._credential("no-expiry-set")

        result = self.env["credential.credential"].cron_check_expiring_credentials()

        self.assertEqual(result["expiring"], 0)
        self.assertEqual(result["warned"], 0)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_archived_credentials_are_ignored(self):
        credential = self._credential("archived", expires_in_days=10, active=False)

        result = self.env["credential.credential"].cron_check_expiring_credentials()

        self.assertEqual(result["warned"], 0)
        self.assertFalse(credential.date_expiry_warned)

    def test_warning_context_is_empty_without_an_enriching_module(self):
        credential = self._credential("plain")
        context = credential._expiry_warning_context()
        self.assertIsInstance(context, str)
        if "endpoint_id" not in credential._fields:
            self.assertEqual(context, "")
