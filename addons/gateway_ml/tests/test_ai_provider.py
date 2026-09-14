from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.gateway_ml.tools.ai_clients import (
    AI_CLIENT_REGISTRY,
    BaseAIClient,
    ClaudeClient,
    DeepgramClient,
    register_ai_client,
)


@tagged("post_install", "-at_install")
class TestAIProviderStatistics(TransactionCase):
    def setUp(self):
        super().setUp()
        self.provider = self.env["gateway.ml.provider"].search(
            [("code", "=", "claude")], limit=1
        )
        if not self.provider:
            self.skipTest("claude provider seed missing")
        self.service = self.provider.endpoint_id
        self.env["integration.exchange"].search(
            [("channel_id", "=", f"integration.service,{self.service.id}")]
        ).unlink()

    def _log(self, when, status_code, duration_ms):
        log = self.env["integration.exchange"].create(
            {
                "direction": "outbound",
                "channel_id": f"integration.service,{self.service.id}",
                "status_code": status_code,
                "state": "success" if status_code < 400 else "failed",
                "duration_ms": duration_ms,
            }
        )
        self.env.cr.execute(
            "UPDATE integration_exchange SET timestamp = %s WHERE id = %s",
            (when, log.id),
        )
        return log

    def test_statistics_are_delegated_not_redeclared(self):
        for name in ("total_requests", "success_rate", "avg_response_time"):
            field = self.env["gateway.ml.provider"]._fields[name]
            self.assertTrue(
                field.inherited,
                f"{name} must be delegated to integration.service, not "
                f"redeclared on gateway.ml.provider -- two computes over the same rows "
                f"produced two different answers.",
            )

    def test_total_cost_is_gone(self):
        self.assertNotIn("total_cost", self.env["gateway.ml.provider"]._fields)

    def test_provider_and_service_agree(self):
        now = fields.Datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for i in range(3):
            self._log(now - timedelta(hours=i + 1), 200, 100.0)
        for i in range(4):
            self._log(month_start - timedelta(days=40, hours=i), 500, 900.0)

        self.env.invalidate_all()
        self.assertEqual(self.provider.total_requests, self.service.total_requests)
        self.assertEqual(self.provider.success_rate, self.service.success_rate)
        self.assertEqual(
            self.provider.avg_response_time, self.service.avg_response_time
        )

    def test_window_is_the_current_month(self):
        now = fields.Datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._log(now - timedelta(hours=1), 200, 100.0)
        self._log(month_start - timedelta(days=40), 500, 900.0)

        self.env.invalidate_all()
        self.assertEqual(self.provider.total_requests, 1)
        self.assertEqual(self.provider.success_rate, 100.0)


@tagged("post_install", "-at_install")
class TestAIProviderClientHook(TransactionCase):
    def test_every_seeded_provider_resolves_to_a_client_class(self):
        for provider in self.env["gateway.ml.provider"].search([]):
            self.assertIn(
                provider.code,
                AI_CLIENT_REGISTRY,
                f"provider {provider.code} has no registered client",
            )

    def test_deepgram_is_registered(self):
        self.assertIs(AI_CLIENT_REGISTRY.get("deepgram"), DeepgramClient)

    def test_hook_returns_the_registered_class(self):
        provider = self.env["gateway.ml.provider"].search(
            [("code", "=", "claude")], limit=1
        )
        if not provider:
            self.skipTest("claude provider seed missing")
        self.assertIs(AI_CLIENT_REGISTRY[provider.code], ClaudeClient)

    def test_unknown_provider_raises_a_named_error(self):
        service = self.env["integration.service"].create(
            {
                "name": "Nowhere AI",
                "code": "nowhere_ai",
                "endpoint_url": "https://example.invalid",
            }
        )
        provider = self.env["gateway.ml.provider"].create({"endpoint_id": service.id})
        with self.assertRaises(UserError) as ctx:
            provider._get_ai_client()
        self.assertIn("nowhere_ai", str(ctx.exception))

    def test_registry_refuses_a_non_client(self):
        class NotAClient:
            pass

        with self.assertRaises(TypeError):
            register_ai_client("bogus", NotAClient)
        self.assertNotIn("bogus", AI_CLIENT_REGISTRY)

    def test_registry_accepts_a_downstream_client(self):
        class ExtraClient(BaseAIClient):
            ENDPOINT_CODE = "extra_probe"
            FALLBACK_MODEL = "extra-1"

        try:
            register_ai_client("extra_probe", ExtraClient)
            self.assertIs(AI_CLIENT_REGISTRY["extra_probe"], ExtraClient)
        finally:
            AI_CLIENT_REGISTRY.pop("extra_probe", None)


@tagged("post_install", "-at_install")
class TestSeededDefaultsMatchTheCatalog(TransactionCase):
    def _catalog_pairs(self):
        from odoo.addons.gateway_ml.tools.vendor_catalog import PROVIDERS

        return [
            (spec["chat_service"], spec["chat_model"])
            for spec in PROVIDERS.values()
            if spec.get("chat_service") and spec.get("chat_model")
        ]

    def test_every_seeded_provider_agrees_with_the_catalog(self):
        checked = 0
        for code, catalog_model in self._catalog_pairs():
            provider = self.env["gateway.ml.provider"].search(
                [("endpoint_id.code", "=", code)], limit=1
            )
            if not provider:
                continue
            with self.subTest(service=code):
                self.assertEqual(
                    provider.default_model_id.code,
                    catalog_model,
                    f"gateway.ml.provider.default_model_id for '{code}' disagrees with "
                    f"vendor_catalog. Change the catalog and re-seed, or add a "
                    f"migration — do not let the two answer differently.",
                )
                checked += 1
        self.assertTrue(checked, "no seeded provider matched a catalog vendor")

    def test_the_catalog_answers_when_no_provider_row_exists(self):
        from odoo.addons.gateway_ml.tools.ai_clients import OpenAIClient

        client = OpenAIClient.__new__(OpenAIClient)
        client.env = self.env
        client.ENDPOINT_CODE = "openai"
        client._default_model = ""
        self.assertEqual(client._resolve_model(), "gpt-5.6-luna")

    def test_a_client_on_a_wire_the_catalog_does_not_describe_keeps_its_own(self):
        from odoo.addons.gateway_ml.tools.ai_clients import DeepgramClient

        client = DeepgramClient.__new__(DeepgramClient)
        client.env = self.env
        client._default_model = ""
        self.assertIsNone(client._catalog_default_model())
        self.assertEqual(client._resolve_model(), "nova-3")

    def test_gemini_resolves_the_catalogs_model_whichever_wire_it_speaks(self):
        from odoo.addons.gateway_ml.tools.ai_clients import GeminiClient
        from odoo.addons.gateway_ml.tools.vendor_catalog import PROVIDERS

        client = GeminiClient.__new__(GeminiClient)
        client.env = self.env
        client._default_model = ""
        self.assertEqual(client._resolve_model(), PROVIDERS["gemini"]["chat_model"])
