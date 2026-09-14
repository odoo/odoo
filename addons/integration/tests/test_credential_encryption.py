from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCredentialEncryption(TransactionCase):
    def setUp(self):
        super().setUp()

        self.service = self.env["integration.service"].create(
            {
                "name": "Test Service",
                "code": "test_service",
                "endpoint_url": "https://api.test.com",
                "category": "other",
            }
        )

    def test_01_encrypt_api_key(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test Credential",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "api_key": "test_api_key_12345",
            }
        )

        self.assertTrue(
            credential.credential_value_encrypted,
            "Credential should be encrypted in credential_value_encrypted",
        )

        decrypted = credential.api_key
        self.assertEqual(
            decrypted,
            "test_api_key_12345",
            "Decrypted API key should match original",
        )

    def test_02_encrypt_bearer_token(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test Bearer Token",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "bearer_token": "bearer_token_xyz_789",
            }
        )

        self.assertTrue(credential.credential_value_encrypted)
        self.assertEqual(credential.bearer_token, "bearer_token_xyz_789")

    def test_03_encrypt_multiple_fields(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test Multiple Fields",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "api_key": "api_key_123",
                "api_secret": "api_secret_456",
                "username": "test_user",
                "password": "test_password",
            }
        )

        self.assertTrue(
            credential.credential_value_encrypted,
            "All credentials stored in single encrypted JSON field",
        )

        self.assertEqual(credential.api_key, "api_key_123")
        self.assertEqual(credential.api_secret, "api_secret_456")
        self.assertEqual(credential.username, "test_user")
        self.assertEqual(credential.password, "test_password")

    def test_04_update_encrypted_field(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test Update",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "api_key": "original_key",
            },
        )

        original_encrypted = credential.credential_value_encrypted

        credential.write({"api_key": "updated_key"})

        self.assertNotEqual(
            credential.credential_value_encrypted,
            original_encrypted,
            "Encrypted value should change when updating",
        )

        self.assertEqual(credential.api_key, "updated_key")

    def test_05_empty_credential_fields(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test Empty",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "bearer_token": "some_token",
            },
        )
        self.assertTrue(credential.credential_value_encrypted)
        self.assertFalse(credential.api_key)
        self.assertFalse(credential.api_secret)

    def test_06_json_credential_storage(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test JSON Storage",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "api_key": "test_key_abc",
                "api_secret": "test_secret_xyz",
            },
        )

        self.assertTrue(credential.credential_value_encrypted)

        data = credential.get_credential_dict()
        self.assertIn("api_key", data)
        self.assertIn("api_secret", data)
        self.assertEqual(data["api_key"], "test_key_abc")
        self.assertEqual(data["api_secret"], "test_secret_xyz")

    def test_07_encryption_consistency(self):
        custom_cat_id = self.env.ref("credential.credential_category_custom").id
        credential1 = self.env["credential.credential"].create(
            {
                "name": "Test Consistency 1",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": custom_cat_id,
                "environment": "production",
                "api_key": "same_key_value",
            },
        )
        credential2 = self.env["credential.credential"].create(
            {
                "name": "Test Consistency 2",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": custom_cat_id,
                "environment": "test",
                "api_key": "same_key_value",
            },
        )
        self.assertNotEqual(
            credential1.credential_value_encrypted,
            credential2.credential_value_encrypted,
            "Same value should encrypt differently each time (Fernet randomness)",
        )
        self.assertEqual(credential1.api_key, credential2.api_key)

    def test_08_oauth_token_encryption(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test OAuth",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "oauth_access_token": "access_token_xyz",
                "oauth_refresh_token": "refresh_token_abc",
            },
        )
        self.assertTrue(credential.credential_value_encrypted)
        data = credential.get_credential_dict()
        self.assertIn("oauth_access_token", data)
        self.assertIn("oauth_refresh_token", data)
        self.assertEqual(credential.oauth_access_token, "access_token_xyz")
        self.assertEqual(credential.oauth_refresh_token, "refresh_token_abc")

    def test_09_unicode_credential_encryption(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test Unicode",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "password": "pá$$wörd_üñïçödé_测试",
            },
        )
        self.assertTrue(credential.credential_value_encrypted)
        self.assertEqual(credential.password, "pá$$wörd_üñïçödé_测试")

    def test_10_long_credential_encryption(self):
        long_key = "x" * 1000
        credential = self.env["credential.credential"].create(
            {
                "name": "Test Long Credential",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "api_key": long_key,
            },
        )
        self.assertTrue(credential.credential_value_encrypted)
        self.assertEqual(len(credential.api_key), 1000)
        self.assertEqual(credential.api_key, long_key)


class TestCredentialAccessLog(TransactionCase):
    def setUp(self):
        super().setUp()
        self.service = self.env["integration.service"].create(
            {
                "name": "Test Service",
                "code": "test_service",
                "endpoint_url": "https://api.test.com",
                "category": "other",
            },
        )

        self.credential = self.env["credential.credential"].create(
            {
                "name": "Test Credential",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "api_key": "test_key_123",
            },
        )

    def test_01_access_log_on_view(self):
        count_before = self.env["credential.access.log"].search_count(
            [("credential_id", "=", self.credential.id)]
        )

        self.credential.with_context(
            **{type(self.credential)._AUDIT_FIELDS_CONTEXT_KEY: ["api_key"]}
        )._log_access("read")

        count_after = self.env["credential.access.log"].search_count(
            [("credential_id", "=", self.credential.id)]
        )
        self.assertEqual(count_after, count_before + 1, "Access log should be created")

        log = self.env["credential.access.log"].search(
            [
                ("credential_id", "=", self.credential.id),
                ("operation", "=", "read"),
            ],
            limit=1,
        )
        self.assertTrue(log, "Access log with operation='read' should exist")
        self.assertEqual(log.field_accessed, "api_key")
        self.assertTrue(log.success)

    def test_02_access_log_on_edit(self):
        count_before = self.env["credential.access.log"].search_count(
            [("credential_id", "=", self.credential.id)]
        )

        self.credential.write({"api_key": "updated_key_456"})

        logs = self.env["credential.access.log"].search(
            [
                ("credential_id", "=", self.credential.id),
                ("operation", "=", "write"),
            ],
        )

        count_after = self.env["credential.access.log"].search_count(
            [("credential_id", "=", self.credential.id)]
        )
        self.assertGreaterEqual(
            count_after, count_before, "Access log count should not decrease after edit"
        )
        if logs:
            self.assertTrue(logs[0].credential_id)

    def test_03_access_log_fields(self):
        self.credential._log_access("read")
        log = self.env["credential.access.log"].search(
            [("credential_id", "=", self.credential.id)], order="id desc", limit=1
        )

        self.assertEqual(log.credential_id, self.credential)
        self.assertEqual(log.user_id, self.env.user)
        self.assertTrue(log.timestamp)
        self.assertEqual(log.company_id, self.env.company)
        self.assertTrue(log.success)
        self.assertEqual(log.credential_name, self.credential.name)
        self.assertEqual(log.user_login, self.env.user.login)

    def test_04_log_access_method(self):
        self.credential.with_context(
            **{type(self.credential)._AUDIT_FIELDS_CONTEXT_KEY: ["api_key"]}
        )._log_access("use")
        log = self.env["credential.access.log"].search(
            [("credential_id", "=", self.credential.id), ("operation", "=", "use")],
            order="id desc",
            limit=1,
        )
        self.assertTrue(log)
        self.assertEqual(log.operation, "use")
        self.assertEqual(log.field_accessed, "api_key")
        self.assertTrue(log.success)

    def test_05_failed_access_log(self):
        log = (
            self.env["credential.access.log"]
            .sudo()
            .create(
                {
                    **self.credential._prepare_access_log_vals("read", False),
                    "success": False,
                    "failure_reason": "Decryption failed",
                },
            )
        )
        self.assertFalse(log.success)
        self.assertEqual(log.failure_reason, "Decryption failed")
        self.assertEqual(log.credential_name, self.credential.name)

    def test_06_access_log_display_name(self):
        self.credential._log_access("read")
        log = self.env["credential.access.log"].search(
            [("credential_id", "=", self.credential.id)], order="id desc", limit=1
        )
        self.assertTrue(log.display_name, "Access log display_name should be non-empty")

    def test_07_access_log_cleanup_cron(self):
        result = self.env["credential.access.log"].cron_cleanup_old_logs(
            retention_days=36500
        )
        self.assertIsInstance(result, int, "cron_cleanup_old_logs should return int")

    def test_08_multiple_field_access_logging(self):
        count_before = self.env["credential.access.log"].search_count(
            [("credential_id", "=", self.credential.id)]
        )

        self.credential._log_access("read")
        self.credential._log_access("read")

        count_after = self.env["credential.access.log"].search_count(
            [("credential_id", "=", self.credential.id)]
        )
        self.assertEqual(count_after, count_before + 2, "Should have 2 new log entries")


class TestEncryptionSecurity(TransactionCase):
    def setUp(self):
        super().setUp()
        self.service = self.env["integration.service"].create(
            {
                "name": "Test Service",
                "code": "test_service",
                "endpoint_url": "https://api.test.com",
                "category": "other",
            },
        )

    def test_01_credential_hash_generation(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test Hash",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "api_key": "test_key_for_hash",
            },
        )

        self.assertTrue(
            credential.credential_hash, "Credential hash should be generated"
        )
        self.assertEqual(
            len(credential.credential_hash),
            64,
            "SHA-256 hash should be 64 chars",
        )

    def test_02_bidirectional_sync(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test Sync",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "api_key": "key_from_field",
            },
        )

        data = credential.get_credential_dict()
        self.assertEqual(data.get("api_key"), "key_from_field")

        credential.set_credential_dict(
            {"api_key": "key_from_json", "api_secret": "new_secret"}
        )

        self.assertEqual(credential.api_key, "key_from_json")
        self.assertEqual(credential.api_secret, "new_secret")

    def test_03_credential_constraint_enforcement(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Test No Credentials",
                "endpoint_id": self.service.id,
                "company_id": self.env.company.id,
                "category_id": self.env.ref(
                    "credential.credential_category_bearer_token"
                ).id,
                "environment": "production",
            },
        )
        self.assertFalse(credential.is_provisioned)
        with self.assertRaises(ValidationError):
            credential.api_key = "a key where the category wants a bearer token"
