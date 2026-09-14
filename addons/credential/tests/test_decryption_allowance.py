from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.rate_limit.tools import get_caller_rate_limiter


@tagged("post_install", "-at_install")
class TestDecryptionAllowance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env.ref("credential.credential_category_api_key")

    def _credential(self, name, cap=3):
        credential = self.env["credential.credential"].create(
            {
                "name": name,
                "category_id": self.category.id,
                "credential_value": "PLAINTEXT",
            }
        )
        credential.sudo().write(
            {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": cap}
        )
        self.env.flush_all()
        return credential

    def _read(self, credential):
        credential.invalidate_recordset(["cached_plaintext", "credential_value"])
        return credential.credential_value

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_the_cap_denies_past_its_capacity(self):
        credential = self._credential("cap denies")

        for attempt in range(3):
            self.assertEqual(self._read(credential), "PLAINTEXT", f"read {attempt + 1}")

        with self.assertRaises(ValidationError):
            self._read(credential)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_the_cap_survives_losing_the_registry_limiter(self):
        credential = self._credential("cap survives")
        for _ in range(3):
            self._read(credential)

        registry = self.env.registry
        get_caller_rate_limiter(self.env)._attempts.clear()
        if hasattr(registry, "_inbound_caller_rate_limiter"):
            del registry._inbound_caller_rate_limiter

        with self.assertRaises(ValidationError):
            self._read(credential)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_the_allowance_is_per_credential_and_user(self):
        spent = self._credential("cap spent")
        fresh = self._credential("cap fresh")

        for _ in range(3):
            self._read(spent)
        with self.assertRaises(ValidationError):
            self._read(spent)

        self.assertEqual(
            self._read(fresh),
            "PLAINTEXT",
            "the allowance is keyed on (credential, user), so another "
            "credential is unaffected",
        )

    def test_a_denial_is_audited_on_a_real_cursor(self):
        registry = self.env.registry
        name = "cap audited real cursor"

        with registry.cursor() as cr:
            env = self.env(cr=cr)
            credential = env["credential.credential"].create(
                {
                    "name": name,
                    "category_id": self.category.id,
                    "credential_value": "PLAINTEXT",
                }
            )
            credential.sudo().write(
                {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": 2}
            )
            credential_id = credential.id
            cr.commit()

        try:
            with registry.cursor() as cr:
                env = self.env(cr=cr)
                credential = env["credential.credential"].browse(credential_id)
                for _ in range(2):
                    credential.invalidate_recordset(
                        ["cached_plaintext", "credential_value"]
                    )
                    self.assertEqual(credential.credential_value, "PLAINTEXT")

                credential.invalidate_recordset(
                    ["cached_plaintext", "credential_value"]
                )
                with self.assertRaises(ValidationError):
                    _ = credential.credential_value
                cr.commit()

            with registry.cursor() as cr:
                env = self.env(cr=cr)
                rows = (
                    env["credential.access.log"]
                    .sudo()
                    .search_count(
                        [
                            ("credential_id", "=", credential_id),
                            ("operation", "=", "read_rate_limited"),
                        ]
                    )
                )
                self.assertEqual(
                    rows, 1, "a denied decryption must leave exactly one row"
                )
        finally:
            with registry.cursor() as cr:
                cr.execute(
                    "DELETE FROM credential_access_log WHERE credential_id = %s",
                    [credential_id],
                )
                cr.execute(
                    "DELETE FROM rate_limit_bucket WHERE bucket_key LIKE %s",
                    [f"credential.credential.decrypt:{credential_id}:%"],
                )
                cr.execute(
                    "DELETE FROM credential_credential WHERE id = %s", [credential_id]
                )
                cr.commit()

    def test_rate_limiting_off_means_no_bucket_at_all(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "cap disabled",
                "category_id": self.category.id,
                "credential_value": "PLAINTEXT",
            }
        )
        credential.sudo().write({"decrypt_rate_limit_enabled": False})
        self.env.flush_all()

        buckets = self.env["rate.limit.bucket"].sudo()
        key = f"credential.credential.decrypt:{credential.id}:{self.env.uid}"
        for _ in range(10):
            self.assertEqual(self._read(credential), "PLAINTEXT")

        self.assertFalse(
            buckets.search([("bucket_key", "=", key)]),
            "a disabled cap must not leave rows behind to garbage-collect",
        )
