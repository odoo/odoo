from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.gateway_ml.tools.ai_clients import (
    ClaudeClient,
    DeepgramClient,
    GeminiClient,
    OpenAICompatibleClient,
    get_client_class,
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
            with self.subTest(provider=provider.code):
                self.assertTrue(get_client_class(provider))

    def test_the_client_is_the_wire_of_the_providers_own_service(self):
        for xmlid, expected in (
            ("gateway_ml.ai_provider_anthropic", ClaudeClient),
            ("gateway_ml.ai_provider_openai", OpenAICompatibleClient),
            ("gateway_ml.ai_provider_groq", OpenAICompatibleClient),
            ("gateway_ml.ai_provider_moonshot", OpenAICompatibleClient),
            ("gateway_ml.ai_provider_deepseek", OpenAICompatibleClient),
            ("gateway_ml.ai_provider_google", GeminiClient),
            ("gateway_ml.ai_provider_deepgram", DeepgramClient),
        ):
            with self.subTest(provider=xmlid):
                self.assertIs(get_client_class(self.env.ref(xmlid)), expected)

    def test_a_shared_wire_client_is_bound_to_the_providers_service(self):
        provider = self.env.ref("gateway_ml.ai_provider_groq")
        with patch(
            "odoo.addons.gateway_ml.tools.ai_clients.base.get_api_client"
        ) as factory:
            client = provider._get_ai_client()
        self.assertIsInstance(client, OpenAICompatibleClient)
        self.assertEqual(client.ENDPOINT_CODE, "groq")
        self.assertEqual(factory.call_args.args[1], "groq")
        self.assertEqual(client._provider(), provider)

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


@tagged("post_install", "-at_install")
class TestSeededDefaultsMatchTheChatOperation(TransactionCase):
    def test_every_provider_defaults_to_its_chat_operations_model(self):
        checked = 0
        for provider in self.env["gateway.ml.provider"].search([]):
            chat = provider.service_ids.filtered(lambda row: row.operation == "chat")
            if not chat:
                continue
            with self.subTest(provider=provider.code):
                self.assertEqual(
                    provider.default_model_id,
                    chat.model_id,
                    f"gateway.ml.provider.default_model_id for '{provider.code}' "
                    f"disagrees with its chat operation. Change both in one "
                    f"migration — do not let the two answer differently.",
                )
                checked += 1
        self.assertTrue(checked, "no seeded provider carries a chat operation")

    def test_the_chat_operation_answers_when_the_provider_names_no_default(self):
        client = OpenAICompatibleClient.__new__(OpenAICompatibleClient)
        client.env = self.env
        client.ENDPOINT_CODE = "openai"
        client._default_model = ""
        self.assertEqual(client._resolve_model(), "gpt-5.6-luna")

    def test_a_client_without_a_chat_operation_keeps_its_own(self):
        from odoo.addons.gateway_ml.tools.ai_clients import DeepgramClient

        client = DeepgramClient.__new__(DeepgramClient)
        client.env = self.env
        client._default_model = ""
        self.assertIsNone(client._operation_default_model())
        self.assertEqual(client._resolve_model(), "nova-3")

    def test_gemini_resolves_its_chat_model_whichever_wire_it_speaks(self):
        from odoo.addons.gateway_ml.tools.ai_clients import GeminiClient

        client = GeminiClient.__new__(GeminiClient)
        client.env = self.env
        client._default_model = ""
        self.assertEqual(
            client._resolve_model(),
            self.env.ref("gateway_ml.ai_provider_google")
            ._service_for("chat")
            .model_id.code,
        )
