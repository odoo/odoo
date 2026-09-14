from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tools.ai_clients.claude import ClaudeClient
from odoo.addons.gateway_ml.tools.vendor_catalog import (
    CHAT_TIMEOUT,
    PROVIDERS,
    TRANSCRIBE_TIMEOUT,
    UNTIMED_TRANSCRIPTION_MODELS,
)

CATALOG_PROVIDERS = {
    "groq": "gateway_ml.ai_provider_groq",
    "gemini": "gateway_ml.ai_provider_google",
    "openai": "gateway_ml.ai_provider_openai",
    "deepseek": "gateway_ml.ai_provider_deepseek",
    "moonshot": "gateway_ml.ai_provider_moonshot",
    "claude": "gateway_ml.ai_provider_anthropic",
}

WIRES = {"openai": "openai_compatible", "anthropic": "anthropic_messages"}


@tagged("post_install", "-at_install")
class TestProviderServicesMatchTheCatalog(TransactionCase):
    def test_every_catalog_chat_is_a_row(self):
        for code, xmlid in CATALOG_PROVIDERS.items():
            spec = PROVIDERS[code]
            with self.subTest(provider=code):
                chat = self.env.ref(xmlid)._service_for("chat")
                self.assertEqual(chat.service_id.code, spec["chat_service"])
                self.assertEqual(chat.path, spec["chat_path"])
                self.assertEqual(chat.wire, WIRES[spec["wire"]])
                self.assertEqual(chat.model_id.code, spec["chat_model"])
                self.assertEqual(chat.timeout, spec.get("chat_timeout") or CHAT_TIMEOUT)
                model = chat.model_id
                self.assertEqual(model.request_extra or {}, spec.get("extra") or {})
                self.assertEqual(
                    model.max_tokens_param, spec.get("max_tokens_param", "max_tokens")
                )
                self.assertEqual(model.min_max_tokens, spec.get("min_max_tokens") or 0)

    def test_every_catalog_transcription_is_a_row(self):
        for code, xmlid in CATALOG_PROVIDERS.items():
            spec = PROVIDERS[code]
            if not spec.get("audio"):
                continue
            with self.subTest(provider=code):
                transcribe = self.env.ref(xmlid)._service_for("transcribe")
                self.assertEqual(transcribe.service_id.code, spec["audio_service"])
                self.assertEqual(transcribe.path, spec["audio_path"])
                self.assertEqual(transcribe.model_id.code, spec["audio_model"])
                self.assertEqual(
                    transcribe.timeout, spec.get("audio_timeout") or TRANSCRIBE_TIMEOUT
                )

    def test_the_timed_transcription_model_is_the_catalogs_cues_model(self):
        timed = self.env.ref("gateway_ml.ai_provider_openai")._service_for(
            "transcribe_timed"
        )

        self.assertEqual(timed.model_id.code, PROVIDERS["openai"]["cues_model"])
        self.assertTrue(timed.model_id.has_timestamps)

    def test_an_untimed_transcription_model_reads_languages_as_a_list(self):
        rows = self.env["gateway.ml.model"].search(
            [("code", "in", list(UNTIMED_TRANSCRIPTION_MODELS))]
        )

        self.assertTrue(rows)
        self.assertEqual(set(rows.mapped("language_form_key")), {"languages[]"})

    def test_claude_rows_carry_the_clients_quirks(self):
        for model in self.env["gateway.ml.model"].search(
            [("provider_id", "=", self.env.ref("gateway_ml.ai_provider_anthropic").id)]
        ):
            with self.subTest(model=model.code):
                self.assertEqual(
                    model.sampling_params,
                    model.code not in ClaudeClient.NO_SAMPLING_PARAMS,
                )
                self.assertEqual(
                    model.forced_tool_choice,
                    model.code not in ClaudeClient.NO_FORCED_TOOL_CHOICE,
                )


@tagged("post_install", "-at_install")
class TestProviderServiceRules(TransactionCase):
    def test_a_provider_that_lacks_an_operation_says_so(self):
        with self.assertRaises(UserError):
            self.env.ref("gateway_ml.ai_provider_anthropic")._service_for("transcribe")

    def test_a_default_model_must_belong_to_the_provider(self):
        chat = self.env.ref("gateway_ml.ai_provider_groq")._service_for("chat")

        with self.assertRaises(ValidationError):
            chat.model_id = self.env.ref("gateway_ml.ai_model_claude_sonnet_5")
