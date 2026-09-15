from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class HealthValidationCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category_custom = cls.env.ref("credential.credential_category_custom")

    @classmethod
    def _make_credential(cls, name, **vals):
        return cls.env["credential.credential"].create(
            {
                "name": name,
                "category_id": cls.category_custom.id,
                **vals,
            },
        )


class TestActionValidateCredential(HealthValidationCommon):
    def test_category_without_probe_stays_unknown(self):
        credential = self._make_credential("Custom cred without probe")

        result = credential._probe_health()

        self.assertTrue(result["not_implemented"])
        self.assertFalse(result["success"])
        self.assertIn("No built-in validation", result["message"])
        self.assertEqual(credential.health_status, "unknown")
        self.assertIn("No built-in validation", credential.health_message)
        self.assertTrue(credential.last_health_check)


class TestCronValidateCredentials(HealthValidationCommon):
    def test_cron_scopes_by_auto_validate_flag(self):
        probed = self._make_credential("Cron probed", auto_validate_health=True)
        excluded = self._make_credential("Cron excluded")

        result = self.env["credential.credential"]._cron_probe_credentials()

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["healthy"], 0)
        self.assertEqual(probed.health_status, "unknown")
        self.assertTrue(probed.last_health_check)
        self.assertFalse(excluded.last_health_check)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_cron_swallows_validation_exception(self):
        Credential = self.env["credential.credential"]
        credential = self._make_credential("Cron crashing", auto_validate_health=True)

        with patch.object(
            type(credential),
            "_probe_health",
            side_effect=ValueError("boom"),
        ):
            result = Credential._cron_probe_credentials()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["errors"], 1)


class TestGetCredentialDict(HealthValidationCommon):
    def test_key_lookup_returns_value_and_default(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Basic auth for key lookup",
                "category_id": self.env.ref(
                    "credential.credential_category_basic_auth"
                ).id,
                "username": "svc-user",
                "password": "svc-pass",
            },
        )
        data = credential.get_credential_dict()
        self.assertEqual(data.get("username"), "svc-user")
        self.assertEqual(data.get("missing", "dflt"), "dflt")

    def test_simple_storage_never_synthesizes_dict_view(self):
        credential = self._make_credential(
            "Simple storage for key lookup",
            credential_value="secret-value",
        )

        self.assertEqual(credential.storage_method, "simple")
        self.assertEqual(credential.get_credential_dict(), {})
