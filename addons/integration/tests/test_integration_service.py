from psycopg import IntegrityError

from odoo.exceptions import ValidationError
from odoo.libs.logging import mute_logger
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.integration.tools.exceptions import CommError


class TestIntegrationService(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

    def _create_service(self, **kwargs):
        default_vals = {
            "name": "Test Service",
            "code": "test_service",
            "endpoint_url": "https://api.test.com",
            "company_id": self.company.id,
        }
        default_vals.update(kwargs)
        return self.env["integration.service"].create(default_vals)

    def test_create_service(self):
        service = self._create_service()

        self.assertEqual(service.name, "Test Service")
        self.assertEqual(service.code, "test_service")
        self.assertEqual(service.endpoint_url, "https://api.test.com")
        self.assertTrue(service.active)

    @mute_logger("odoo.db.cursor")
    def test_code_uniqueness_constraint(self):
        self._create_service(code="unique_code")

        try:
            self._create_service(code="unique_code", name="Another Service")
        except IntegrityError, ValidationError:
            pass
        else:
            self.fail("Duplicate service code should raise")

    def test_code_format_validation_valid(self):
        valid_codes = ["simple", "with_underscore", "test123", "api_v1"]

        for i, code in enumerate(valid_codes):
            service = self._create_service(
                code=code,
                name=f"Service {i}",
            )
            self.assertEqual(service.code, code)

    def test_code_format_validation_invalid(self):
        invalid_codes = [
            "With-Dash",
            "WithCaps",
            "with spaces",
            "special@char",
        ]

        for code in invalid_codes:
            with self.assertRaises(ValidationError):
                self._create_service(code=code)

    def test_https_enforcement_production(self):
        with self.assertRaises(ValidationError):
            self._create_service(
                code="http_service",
                endpoint_url="http://api.test.com",
            )

    @mute_logger("odoo.addons.integration.models.integration_service")
    def test_https_enforcement_localhost_allowed(self):
        service = self._create_service(
            code="localhost_service",
            endpoint_url="http://localhost:8080",
        )
        self.assertIn("localhost", service.endpoint_url)

    def test_category_selection(self):
        categories = [
            "payment",
            "delivery",
            "communication",
            "social",
            "tax",
            "calendar",
            "cloud",
            "ai",
            "geocoding",
            "analytics",
            "other",
        ]

        for i, category in enumerate(categories):
            service = self._create_service(
                code=f"service_{i}",
                name=f"Service {i}",
                category=category,
            )
            self.assertEqual(service.category, category)

    def test_environment_selection(self):
        environments = ["test", "staging", "production"]

        for i, env in enumerate(environments):
            service = self._create_service(
                code=f"env_service_{i}",
                name=f"Service {i}",
                environment=env,
            )
            self.assertEqual(service.environment, env)

    def test_timeout_defaults(self):
        service = self._create_service(code="timeout_test")

        self.assertEqual(service.timeout_connect, 10)
        self.assertEqual(service.timeout_read, 30)

    def test_health_check_defaults(self):
        service = self._create_service(code="health_test")

        self.assertTrue(service.health_check_enabled)
        self.assertEqual(service.health_check_interval, 15)
        self.assertTrue(service.is_healthy)

    def test_cache_health_computation_disabled(self):
        service = self._create_service(
            code="cache_disabled",
            cache_enabled=False,
        )
        self.assertFalse(service.cache_health)

    def test_cache_health_computation_healthy(self):
        service = self._create_service(
            code="cache_healthy",
            cache_enabled=True,
            cache_error_count=0,
        )
        self.assertEqual(service.cache_health, "healthy")

    def test_cache_health_computation_degraded(self):
        service = self._create_service(
            code="cache_degraded",
            cache_enabled=True,
        )
        service.cache_error_count = 5
        service._compute_cache_health()

        self.assertEqual(service.cache_health, "degraded")

    def test_cache_health_computation_failed(self):
        service = self._create_service(
            code="cache_failed",
            cache_enabled=True,
        )
        service.cache_error_count = 15
        service._compute_cache_health()

        self.assertEqual(service.cache_health, "failed")

    def test_credential_count_computation(self):
        service = self._create_service(code="cred_count_test")

        self.assertEqual(service.credential_count, 0)

    def test_action_view_credentials(self):
        service = self._create_service(code="view_creds")

        result = service.action_view_credentials()

        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "credential.credential")
        self.assertIn(str(service.id), str(result["domain"]))

    def test_action_view_logs(self):
        service = self._create_service(code="view_logs")

        result = service.action_view_logs()

        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "integration.exchange")
        self.assertIn("outbound", str(result["domain"]))

    def test_action_test_connection_no_credentials(self):
        service = self._create_service(code="no_creds")

        with self.assertRaises(ValidationError):
            service.action_test_connection()

    def test_oauth_configuration_fields(self):
        service = self._create_service(
            code="oauth_test",
            oauth_client_id="test_client_id",
            oauth_auth_endpoint="https://oauth.test.com/authorize",
            oauth_token_endpoint="https://oauth.test.com/token",
            oauth_scope="read write",
        )

        self.assertEqual(service.oauth_client_id, "test_client_id")
        self.assertEqual(
            service.oauth_auth_endpoint, "https://oauth.test.com/authorize"
        )
        self.assertEqual(service.oauth_scope, "read write")

    def test_log_retention_defaults_to_the_global_setting(self):
        service = self._create_service(code="retention_test")

        self.assertEqual(service.log_retention_days, 0)


class TestCacheErrorReset(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

    def test_cron_reset_cache_errors(self):
        service = self.env["integration.service"].create(
            {
                "name": "Cache Error Service",
                "code": "cache_reset_test",
                "endpoint_url": "https://api.test.com",
                "company_id": self.company.id,
                "cache_enabled": True,
            },
        )

        service.write({"cache_error_count": 10})
        self.assertEqual(service.cache_error_count, 10)

        self.env["integration.service"].cron_reset_cache_errors()

        self.assertEqual(service.cache_error_count, 0)


class TestStatisticsComputation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

    def test_statistics_no_logs(self):
        service = self.env["integration.service"].create(
            {
                "name": "Stats Service",
                "code": "stats_test",
                "endpoint_url": "https://api.test.com",
                "company_id": self.company.id,
            },
        )

        self.assertEqual(service.total_requests, 0)
        self.assertEqual(service.success_rate, 0.0)
        self.assertEqual(service.avg_response_time, 0.0)

    def test_statistics_with_logs(self):
        service = self.env["integration.service"].create(
            {
                "name": "Stats Service 2",
                "code": "stats_test_2",
                "endpoint_url": "https://api.test.com",
                "company_id": self.company.id,
            },
        )

        channel_ref = f"integration.service,{service.id}"

        for i in range(10):
            self.env["integration.exchange"].create(
                {
                    "direction": "outbound",
                    "channel_id": channel_ref,
                    "status_code": 200 if i < 8 else 500,
                    "duration_ms": 100 + i * 10,
                    "state": "success" if i < 8 else "failed",
                },
            )

        service._compute_statistics()

        self.assertEqual(service.total_requests, 10)
        self.assertEqual(service.success_rate, 80.0)
        self.assertTrue(service.avg_response_time > 0)


@tagged("post_install", "-at_install")
class TestUnauthenticatedService(TransactionCase):
    def setUp(self):
        super().setUp()
        self.service = self.env["integration.service"].create(
            {
                "name": "Public Feed",
                "code": "public_feed_probe",
                "endpoint_url": "https://example.invalid/live",
                "endpoint_url_test": "https://example.invalid/test",
                "auth_type": "none",
                "environment": "production",
            }
        )

    def test_client_builds_without_a_credential(self):
        client = self.service._get_api_client()
        self.assertFalse(client.credential)

    def test_no_auth_headers_are_invented(self):
        client = self.service._get_api_client()
        headers = client._get_headers()
        self.assertNotIn("Authorization", headers)

    def test_basic_auth_is_none(self):
        self.assertIsNone(self.service._get_api_client()._get_auth())

    def test_service_environment_picks_the_base_url(self):
        self.assertEqual(
            self.service._get_api_client().base_url, "https://example.invalid/live"
        )

        self.service.environment = "test"
        self.assertEqual(
            self.service._get_api_client().base_url, "https://example.invalid/test"
        )

    def test_authenticated_service_still_demands_a_credential(self):
        secured = self.env["integration.service"].create(
            {
                "name": "Secured",
                "code": "secured_probe",
                "endpoint_url": "https://example.invalid",
                "auth_type": "bearer",
            }
        )
        with self.assertRaises(CommError):
            secured._get_api_client()


@tagged("post_install", "-at_install", "integration")
class TestGenericVersionHeaders(TransactionCase):
    def _client_for(self, **vals):
        service = self.env["integration.service"].create(
            {
                "name": "Version Probe",
                "code": "version_probe",
                "endpoint_url": "https://example.invalid/v1",
                "auth_type": "none",
                "environment": "production",
                **vals,
            }
        )
        return service._get_api_client()

    def test_headers_are_sent_by_default(self):
        headers = self._client_for(api_version="2024-01-01")._get_headers()
        self.assertEqual(headers.get("API-Version"), "2024-01-01")
        self.assertEqual(headers.get("X-API-Version"), "2024-01-01")

    def test_opting_out_suppresses_both(self):
        headers = self._client_for(
            api_version="2024-01-01", send_version_headers=False
        )._get_headers()
        self.assertNotIn("API-Version", headers)
        self.assertNotIn("X-API-Version", headers)

    def test_no_version_means_no_headers_either_way(self):
        headers = self._client_for(send_version_headers=True)._get_headers()
        self.assertNotIn("API-Version", headers)

    def test_the_seeded_self_versioning_services_are_opted_out(self):
        for code in ("claude", "gemini"):
            service = self.env["integration.service"].search(
                [("code", "=", code)], limit=1
            )
            if not service:
                continue
            with self.subTest(service=code):
                self.assertTrue(service.api_version)
                self.assertFalse(service.send_version_headers)
                self.assertEqual(
                    service.api_version_header,
                    "anthropic-version" if code == "claude" else False,
                )

    def test_a_named_version_header_carries_the_version_instead(self):
        headers = self._client_for(
            api_version="2023-06-01",
            api_version_header="anthropic-version",
            send_version_headers=False,
        )._get_headers()
        self.assertEqual(headers.get("anthropic-version"), "2023-06-01")
        self.assertNotIn("API-Version", headers)


@tagged("post_install", "-at_install", "integration")
class TestApiKeyHeader(TransactionCase):
    def _credential_for(self, **service_vals):
        service = self.env["integration.service"].create(
            {
                "name": "Key Header Probe",
                "code": "key_header_probe",
                "endpoint_url": "https://example.invalid/v1",
                "auth_type": "api_key",
                "environment": "production",
                **service_vals,
            }
        )
        return self.env["credential.credential"].create(
            {
                "name": "Key Header Probe Credential",
                "endpoint_id": service.id,
                "api_key": "probe-key",
            }
        )

    def test_empty_means_the_generic_pair(self):
        headers = self._credential_for()._get_auth_headers()
        self.assertEqual(headers.get("Authorization"), "Bearer probe-key")
        self.assertEqual(headers.get("X-API-Key"), "probe-key")

    def test_a_scheme_replaces_bearer_in_the_generic_pair(self):
        headers = self._credential_for(api_key_scheme="Token")._get_auth_headers()
        self.assertEqual(headers.get("Authorization"), "Token probe-key")
        self.assertEqual(headers.get("X-API-Key"), "probe-key")

    def test_a_named_header_ignores_the_scheme(self):
        headers = self._credential_for(
            api_key_header="x-api-key", api_key_scheme="Token"
        )._get_auth_headers()
        self.assertEqual(headers.get("x-api-key"), "probe-key")
        self.assertNotIn("Authorization", headers)

    def test_deepgram_is_seeded_with_the_token_scheme(self):
        service = self.env["integration.service"].search(
            [("code", "=", "deepgram")], limit=1
        )
        if not service:
            self.skipTest("gateway_ml not installed")
        self.assertEqual(service.api_key_scheme, "Token")

    def test_a_named_header_replaces_the_generic_pair(self):
        headers = self._credential_for(api_key_header="x-api-key")._get_auth_headers()
        self.assertEqual(headers.get("x-api-key"), "probe-key")
        self.assertNotIn("Authorization", headers)
        self.assertNotIn("X-API-Key", headers)

    def test_the_seeded_vendors_name_their_own_header(self):
        for code, expected in (("claude", "x-api-key"), ("gemini", "x-goog-api-key")):
            service = self.env["integration.service"].search(
                [("code", "=", code)], limit=1
            )
            if not service:
                continue
            with self.subTest(service=code):
                self.assertEqual(service.api_key_header, expected)
