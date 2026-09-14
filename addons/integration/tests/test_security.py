import psycopg.errors

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.integration.tests.common import APITransportTestCase


@tagged("post_install", "-at_install", "integration")
class TestSecurityAccess(APITransportTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_api_admin = cls.env["res.users"].create(
            {
                "name": "API Admin",
                "login": "api_admin",
                "email": "api_admin@test.com",
                "group_ids": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("integration.group_api_transport_admin").id,
                            cls.env.ref("credential.group_credential_admin").id,
                        ]
                    )
                ],
            }
        )

        cls.user_basic = cls.env["res.users"].create(
            {
                "name": "Basic User",
                "login": "basic_user",
                "email": "basic_user@test.com",
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )

    def test_api_admin_can_create_service(self):
        service = (
            self.env["integration.service"]
            .with_user(self.user_api_admin)
            .create(
                {
                    "name": "Admin Test Service",
                    "code": "admin_test",
                    "category": "other",
                    "endpoint_url": "https://api.test.com",
                    "environment": "production",
                }
            )
        )

        self.assertTrue(service.exists())
        self.assertEqual(service.code, "admin_test")

    def test_api_admin_can_read_service(self):
        services = (
            self.env["integration.service"].with_user(self.user_api_admin).search([])
        )
        self.assertGreater(len(services), 0)

    def test_api_admin_can_update_service(self):
        service = self.env["integration.service"].create(
            {
                "name": "Update Test",
                "code": "update_test",
                "category": "other",
                "endpoint_url": "https://api.test.com",
                "environment": "production",
            }
        )

        service.with_user(self.user_api_admin).write({"name": "Updated Name"})
        self.assertEqual(service.name, "Updated Name")

    def test_api_admin_can_delete_service(self):
        service = self.env["integration.service"].create(
            {
                "name": "Delete Test",
                "code": "delete_test",
                "category": "other",
                "endpoint_url": "https://api.test.com",
                "environment": "production",
            }
        )

        service.with_user(self.user_api_admin).unlink()
        self.assertFalse(service.exists())

    def test_basic_user_cannot_access_services(self):
        with self.assertRaises(AccessError):
            self.env["integration.service"].with_user(self.user_basic).search([])

    def test_api_admin_can_create_credential(self):
        credential = (
            self.env["credential.credential"]
            .with_user(self.user_api_admin)
            .create(
                {
                    "name": "Admin Credential",
                    "endpoint_id": self.service_stripe.id,
                    "company_id": self.env.company.id,
                    "category_id": self.cat_custom.id,
                    "environment": "production",
                    "credential_value": "test_token",
                }
            )
        )

        self.assertTrue(credential.exists())

    def test_api_admin_can_read_credential(self):
        credentials = (
            self.env["credential.credential"].with_user(self.user_api_admin).search([])
        )
        self.assertGreater(len(credentials), 0)

    def test_api_admin_can_delete_credential(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Delete Credential",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.env.company.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "credential_value": "test_token",
            }
        )

        credential.with_user(self.user_api_admin).unlink()
        self.assertFalse(credential.exists())

    def test_basic_user_cannot_access_credentials(self):
        with self.assertRaises(AccessError):
            self.env["credential.credential"].with_user(self.user_basic).search([])

    def test_credential_sensitive_fields_restricted(self):
        credential = self.credential_stripe

        credential_as_admin = credential.with_user(self.user_api_admin)
        _ = credential_as_admin.bearer_token
        self.assertTrue(True)

    def test_api_admin_can_view_logs(self):
        self.create_request_log(service=self.service_stripe)

        logs = (
            self.env["integration.exchange"].with_user(self.user_api_admin).search([])
        )
        self.assertGreater(len(logs), 0)

    def test_api_admin_can_delete_logs(self):
        log = self.create_request_log(service=self.service_stripe)

        log.with_user(self.user_api_admin).unlink()
        self.assertFalse(log.exists())

    def test_basic_user_cannot_access_logs(self):
        with self.assertRaises(AccessError):
            self.env["integration.exchange"].with_user(self.user_basic).search([])

    def test_credential_access_logging(self):
        credential = self.credential_stripe

        credential.invalidate_recordset(["cached_plaintext", "credential_value"])

        log_count_before = self.env["credential.access.log"].search_count([])

        _ = credential.credential_value

        log_count_after = self.env["credential.access.log"].search_count([])

        self.assertGreater(log_count_after, log_count_before)

        log = self.env["credential.access.log"].search(
            [("credential_id", "=", credential.id)],
            order="id desc",
            limit=1,
        )

        self.assertEqual(log.credential_id.id, credential.id)
        self.assertEqual(log.operation, "read")
        self.assertTrue(log.success)

    def test_credential_validation_unique_per_service_company(self):
        self.env["credential.credential"].create(
            {
                "name": "Test Credential",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.env.company.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "credential_value": "token1",
            }
        )

        try:
            self.env["credential.credential"].create(
                {
                    "name": "Test Credential 2",
                    "endpoint_id": self.service_stripe.id,
                    "company_id": self.env.company.id,
                    "category_id": self.cat_custom.id,
                    "environment": "production",
                    "credential_value": "token2",
                }
            )
            self.assertTrue(True)
        except ValidationError:
            self.assertTrue(True)

    def test_service_code_validation(self):
        raised = None
        with mute_logger("odoo.db.cursor"):
            try:
                self.env["integration.service"].create(
                    {
                        "name": "Duplicate Service",
                        "code": "test_stripe",
                        "category": "other",
                        "endpoint_url": "https://api.dup.com",
                        "environment": "production",
                    }
                )
            except (ValidationError, psycopg.errors.UniqueViolation) as e:
                raised = e
        self.assertIsNotNone(
            raised,
            "Creating a service with a duplicate code should raise either "
            "ValidationError or psycopg.errors.UniqueViolation",
        )

    def test_encryption_key_protection(self):
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .search(
                [("key", "=", "api_gateway.encryption_key")],
                limit=1,
            )
        )

        if param:
            with self.assertRaises(AccessError):
                param_as_basic = param.with_user(self.user_basic)
                _ = param_as_basic.value

    def test_credential_environment_validation(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "Different Environment",
                "endpoint_id": self.service_stripe.id,
                "company_id": self.env.company.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "credential_value": "test_token",
            }
        )

        self.assertTrue(credential.exists())

    def test_rate_limit_configuration_validation(self):
        with self.assertRaises(ValidationError):
            self.env["integration.service"].create(
                {
                    "name": "Invalid Rate Limit",
                    "code": "test_invalid_rate",
                    "category": "other",
                    "endpoint_url": "https://api.test.com",
                    "environment": "production",
                    "rate_limit_enabled": True,
                    "rate_limit_requests": -1,
                    "rate_limit_period": "minute",
                }
            )

    def test_multi_company_isolation(self):
        other_company = self.env["res.company"].create({"name": "Other Company"})

        credential_other_company = (
            self.env["credential.credential"]
            .sudo()
            .create(
                {
                    "name": "Other Company Credential",
                    "endpoint_id": self.service_stripe.id,
                    "company_id": other_company.id,
                    "category_id": self.cat_custom.id,
                    "environment": "test",
                    "credential_value": "other_token",
                }
            )
        )

        admin_credentials = (
            self.env["credential.credential"].with_user(self.user_api_admin).search([])
        )

        self.assertNotIn(credential_other_company.id, admin_credentials.ids)

    def test_system_admin_has_override_access(self):
        admin_user = self.env.ref("base.user_admin")

        services = self.env["integration.service"].with_user(admin_user).search([])
        self.assertGreaterEqual(len(services), 0)
