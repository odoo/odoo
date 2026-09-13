import os
from unittest.mock import patch

from cryptography.fernet import Fernet

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestHardeningFixesBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_key = Fernet.generate_key().decode()
        cls.env_patcher = patch.dict(
            os.environ, {"ODOO_API_ENCRYPTION_KEY": cls.test_key}, clear=False
        )
        cls.env_patcher.start()
        cls.env["credential.credential"]._invalidate_key_version_cache()
        cls.category_api_key = cls.env.ref("credential.credential_category_api_key")
        cls.category_custom = cls.env.ref("credential.credential_category_custom")

    @classmethod
    def tearDownClass(cls):
        cls.env_patcher.stop()
        cls.env["credential.credential"]._invalidate_key_version_cache()
        super().tearDownClass()


class TestEncryptionKeyCurrentFlag(TestHardeningFixesBase):
    def test_fresh_credential_is_current(self):
        cred = self.env["credential.credential"].create(
            {
                "name": "Fresh Key Cred",
                "category_id": self.category_api_key.id,
                "credential_value": "abc123",
            }
        )
        self.assertTrue(cred.encryption_key_is_current)

    def test_no_payload_counts_as_current(self):
        cred = self.env["credential.credential"].create(
            {
                "name": "No Payload Cred",
                "category_id": self.category_custom.id,
            }
        )
        self.assertFalse(cred.encryption_key_version)
        self.assertTrue(cred.encryption_key_is_current)

    def test_old_key_version_is_not_current(self):
        cred = self.env["credential.credential"].create(
            {
                "name": "Old Key Cred",
                "category_id": self.category_api_key.id,
                "credential_value": "abc123",
            }
        )
        self.assertEqual(cred.encryption_key_version, 1)
        with patch.dict(
            os.environ,
            {
                "ODOO_API_ENCRYPTION_KEY": Fernet.generate_key().decode(),
                "ODOO_API_ENCRYPTION_KEY_V1": self.test_key,
            },
        ):
            self.env["credential.credential"]._invalidate_key_version_cache()
            cred.invalidate_recordset(["encryption_key_is_current"])
            self.assertFalse(cred.encryption_key_is_current)
        self.env["credential.credential"]._invalidate_key_version_cache()

    def test_write_stamps_version_visible_in_same_transaction(self):
        cred = self.env["credential.credential"].create(
            {
                "name": "Stamp Cred",
                "category_id": self.category_custom.id,
            }
        )
        self.env.cr.execute(
            "UPDATE credential_credential SET encryption_key_version = NULL "
            "WHERE id = %s",
            [cred.id],
        )
        cred.invalidate_recordset()
        self.assertFalse(cred.encryption_key_version)

        cred.credential_value = "sealed-now"

        self.assertEqual(cred.encryption_key_version, 1)
        self.assertTrue(cred.encryption_key_is_current)


class TestConsumeTokenCacheConsistency(TestHardeningFixesBase):
    def test_tokens_field_reflects_consumption(self):
        cred = self.env["credential.credential"].create(
            {
                "name": "Bucket Endpoint",
                "category_id": self.category_custom.id,
            }
        )
        bucket = self.env["rate.limit.bucket"].create(
            {
                "bucket_key": f"credential.credential:{cred.id}:global",
                "endpoint_model": "credential.credential",
                "endpoint_id": cred.id,
                "tokens": 5.0,
            }
        )
        self.assertTrue(bucket.consume_token())
        self.assertAlmostEqual(bucket.tokens, 4.0, places=1)
        self.assertTrue(bucket.last_request_at)


class TestValidationWithoutSystemGroup(TestHardeningFixesBase):
    def test_missing_payload_raises_validation_not_access_error(self):
        user = self.env["res.users"].create(
            {
                "name": "Credential User",
                "login": "cred_user_validation_test",
                "group_ids": [
                    (
                        6,
                        0,
                        [self.env.ref("credential.group_credential_user").id],
                    )
                ],
            }
        )
        credential = (
            self.env["credential.credential"]
            .with_user(user)
            .create(
                {
                    "name": "No Payload API Key",
                    "category_id": self.category_api_key.id,
                }
            )
        )
        self.assertFalse(
            credential.is_provisioned,
            "a credential created without a secret is unprovisioned, and "
            "checking that must not read a system-only field on the user's behalf",
        )
        with self.assertRaises(ValidationError) as ctx:
            credential.sudo().write({"api_secret": "secret-without-its-key"})
        self.assertIn("secret value", str(ctx.exception))


class TestAdminGroupImpliesSystem(TestHardeningFixesBase):
    def test_admin_group_implies_group_system(self):
        admin_group = self.env.ref("credential.group_credential_admin")
        system_group = self.env.ref("base.group_system")
        self.assertIn(system_group, admin_group.all_implied_ids)

    def test_admin_can_create_and_read_secret(self):
        user = self.env["res.users"].create(
            {
                "name": "Credential Admin",
                "login": "cred_admin_secret_test",
                "group_ids": [
                    (
                        6,
                        0,
                        [self.env.ref("credential.group_credential_admin").id],
                    )
                ],
            }
        )
        cred = (
            self.env["credential.credential"]
            .with_user(user)
            .create(
                {
                    "name": "Admin Made Cred",
                    "category_id": self.category_api_key.id,
                    "credential_value": "admin-secret",
                }
            )
        )
        self.assertEqual(cred.credential_value, "admin-secret")


class TestBatchDeleteAudit(TestHardeningFixesBase):
    def test_bulk_unlink_writes_one_row_per_credential(self):
        creds = self.env["credential.credential"].create(
            [
                {
                    "name": f"Bulk Delete Cred {i}",
                    "category_id": self.category_custom.id,
                }
                for i in range(3)
            ]
        )
        names = set(creds.mapped("name"))
        creds.unlink()
        rows = self.env["credential.access.log"].search(
            [("operation", "=", "delete"), ("credential_name", "in", list(names))]
        )
        self.assertEqual(set(rows.mapped("credential_name")), names)
        self.assertEqual(len(rows), 3)


class TestRotationMigrationGeneralization(TestHardeningFixesBase):
    def _grant_admin(self):
        self.env.user.group_ids = [
            (
                4,
                self.env.ref("credential.group_credential_admin").id,
            )
        ]

    def test_walker_discovers_consumers_not_the_mixin(self):
        models = self.env["credential.credential"]._get_encryption_migration_models()
        self.assertIn("credential.credential", models)
        self.assertNotIn("mixin.encryption", models)

    def test_null_version_rows_are_eligible(self):
        self._grant_admin()
        cred = self.env["credential.credential"].create(
            {
                "name": "Null Version Cred",
                "category_id": self.category_api_key.id,
                "credential_value": "rotate-me",
            }
        )
        self.env.cr.execute(
            "UPDATE credential_credential SET encryption_key_version = NULL "
            "WHERE id = %s",
            [cred.id],
        )
        cred.invalidate_recordset()
        ciphertext_before = bytes(
            cred.with_context(bin_size=False).credential_value_encrypted
        )

        result = self.env["credential.credential"].action_migrate_encryption_keys()

        cred.invalidate_recordset()
        self.assertNotEqual(
            bytes(cred.with_context(bin_size=False).credential_value_encrypted),
            ciphertext_before,
            "NULL-version row must be re-encrypted",
        )
        self.assertEqual(cred.encryption_key_version, 1)
        self.assertEqual(cred.credential_value, "rotate-me")
        self.assertGreaterEqual(result["migrated"], 1)

    def test_result_contains_per_model_breakdown(self):
        self._grant_admin()
        result = self.env["credential.credential"].action_migrate_encryption_keys()
        self.assertIn("models", result)
        self.assertIn("credential.credential", result["models"])
        per_model = result["models"]["credential.credential"]
        for key in ("total", "eligible", "skipped", "migrated", "failed"):
            self.assertIn(key, per_model)
        for key in ("total", "skipped", "migrated", "failed", "errors"):
            self.assertIn(key, result)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_failed_row_rolls_back_orm_cache_and_is_not_counted_migrated(self):
        self._grant_admin()
        Model = self.env["credential.credential"]
        old_key = self.test_key
        new_key = Fernet.generate_key().decode()

        doomed = Model.create(
            {
                "name": "Doomed Cred",
                "category_id": self.category_api_key.id,
                "credential_value": "keep-me-doomed",
            }
        )
        healthy = Model.create(
            {
                "name": "Healthy Cred",
                "category_id": self.category_api_key.id,
                "credential_value": "keep-me-healthy",
            }
        )
        self.assertEqual(doomed.encryption_key_version, 1)
        self.assertEqual(healthy.encryption_key_version, 1)
        doomed_id = doomed.id

        old_ciphertext = bytes(
            doomed.with_context(bin_size=False).credential_value_encrypted
        )

        orig_stamp = type(Model)._stamp_encryption_key_version

        def stamp_or_raise(self, version):
            if doomed_id in self.ids:
                raise RuntimeError("injected failure after re-encryption")
            return orig_stamp(self, version)

        env_vars = {
            "ODOO_API_ENCRYPTION_KEY": new_key,
            "ODOO_API_ENCRYPTION_KEY_V1": old_key,
        }
        with patch.dict(os.environ, env_vars, clear=True):
            Model._invalidate_key_version_cache()
            self.assertEqual(Model._get_current_encryption_key_version(), 2)
            with patch.object(
                type(Model), "_stamp_encryption_key_version", stamp_or_raise
            ):
                result = Model.action_migrate_encryption_keys()

            self.assertGreaterEqual(result["failed"], 1)
            self.assertTrue(
                any(f"ID: {doomed_id})" in err for err in result["errors"]),
                "the injected failure must surface in the per-row error list",
            )

            self.assertEqual(
                bytes(doomed.with_context(bin_size=False).credential_value_encrypted),
                old_ciphertext,
                "failed row's re-encrypted payload must not survive in the "
                "ORM cache after rollback",
            )

            healthy.invalidate_recordset(["encryption_key_version"])
            self.assertEqual(healthy.encryption_key_version, 2)
            self.assertGreaterEqual(result["migrated"], 1)

        self.env.flush_all()
        Model._invalidate_key_version_cache()
        fresh = Model.browse(doomed_id)
        fresh.invalidate_recordset()
        self.assertEqual(fresh.credential_value, "keep-me-doomed")
        self.assertEqual(fresh.encryption_key_version, 1)


class TestEO78SudoReads(TestHardeningFixesBase):
    def _low_priv_user(self, login):
        return self.env["res.users"].create(
            {
                "name": "Low Priv Credential User",
                "login": login,
                "group_ids": [
                    (
                        6,
                        0,
                        [self.env.ref("credential.group_credential_user").id],
                    )
                ],
            }
        )

    def test_decrypt_value_reads_allow_key_fallback_without_accesserror(self):
        user = self._low_priv_user("eo78_decrypt_char_user")
        cred = self.env["credential.credential"].create(
            {
                "name": "Fallback Char Cred",
                "category_id": self.category_api_key.id,
                "credential_value": "secret-value",
                "allow_key_fallback": False,
            }
        )
        cred.with_user(user)._decrypt_value(
            cred.with_context(bin_size=False).credential_value_encrypted
        )

    def test_decrypt_binary_value_reads_allow_key_fallback_without_accesserror(self):
        user = self._low_priv_user("eo78_decrypt_binary_user")
        cred = self.env["credential.credential"].create(
            {
                "name": "Fallback Binary Cred",
                "category_id": self.category_custom.id,
                "allow_key_fallback": False,
            }
        )
        encrypted = cred._encrypt_binary_value(b"YmluYXJ5LXBheWxvYWQ=")
        cred.with_user(user)._decrypt_binary_value(encrypted)

    def test_onchange_category_id_applies_defaults_without_accesserror(self):
        user = self._low_priv_user("eo78_onchange_user")
        cred = self.env["credential.credential"].new(
            {"name": "Onchange Cred", "category_id": self.category_api_key.id}
        )
        cred_as_user = cred.with_user(user)
        cred_as_user._onchange_category_id()
        self.assertEqual(
            cred_as_user.sudo().decrypt_rate_limit_enabled,
            self.category_api_key.default_decrypt_rate_limit_enabled,
        )
        self.assertEqual(
            cred_as_user.sudo().allow_key_fallback,
            self.category_api_key.default_allow_key_fallback,
        )


class TestRateLimitBucketLockTimeoutScope(TestHardeningFixesBase):
    def test_lock_timeout_reset_after_strict_consume(self):
        cred = self.env["credential.credential"].create(
            {
                "name": "Lock Timeout Scope Cred",
                "category_id": self.category_custom.id,
            }
        )
        self.env.cr.execute("SHOW lock_timeout")
        (before,) = self.env.cr.fetchone()

        bucket = self.env["rate.limit.bucket"].create(
            {
                "bucket_key": f"credential.credential:{cred.id}:global",
                "endpoint_model": "credential.credential",
                "endpoint_id": cred.id,
                "tokens": 5.0,
            }
        )
        self.assertTrue(bucket.consume_token(strict=True))

        self.env.cr.execute("SHOW lock_timeout")
        (after,) = self.env.cr.fetchone()
        self.assertEqual(
            before,
            after,
            "lock_timeout must be reset immediately after the locked query, "
            "not leak into the rest of the transaction",
        )
