from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tools.wire_formats import UNTIMED_TRANSCRIPTION_MODELS

CHAT = {
    "gateway_ml.ai_provider_groq": (
        "https://api.groq.com/openai/v1/chat/completions",
        "openai_compatible",
        "openai/gpt-oss-120b",
        25,
    ),
    "gateway_ml.ai_provider_google": (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "openai_compatible",
        "gemini-3.5-flash-lite",
        25,
    ),
    "gateway_ml.ai_provider_openai": (
        "https://api.openai.com/v1/chat/completions",
        "openai_compatible",
        "gpt-5.6-luna",
        25,
    ),
    "gateway_ml.ai_provider_deepseek": (
        "https://api.deepseek.com/v1/chat/completions",
        "openai_compatible",
        "deepseek-flash",
        25,
    ),
    "gateway_ml.ai_provider_moonshot": (
        "https://api.moonshot.ai/v1/chat/completions",
        "openai_compatible",
        "kimi-k3",
        60,
    ),
    "gateway_ml.ai_provider_anthropic": (
        "https://api.anthropic.com/v1/messages",
        "anthropic_messages",
        "claude-sonnet-5",
        25,
    ),
}

TRANSCRIBE = {
    "gateway_ml.ai_provider_groq": (
        "https://api.groq.com/openai/v1/audio/transcriptions",
        "openai_compatible",
        "whisper-large-v3-turbo",
        30,
    ),
    "gateway_ml.ai_provider_google": (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "gemini_native",
        "gemini-flash-lite-latest",
        90,
    ),
    "gateway_ml.ai_provider_openai": (
        "https://api.openai.com/v1/audio/transcriptions",
        "openai_compatible",
        "gpt-transcribe",
        30,
    ),
}


CHAT_MODEL_SHAPES = {
    "gateway_ml.ai_provider_groq": ({"reasoning_effort": "low"}, "max_tokens", 0),
    "gateway_ml.ai_provider_google": ({"reasoning_effort": "low"}, "max_tokens", 2000),
    "gateway_ml.ai_provider_openai": (
        {"reasoning_effort": "none"},
        "max_completion_tokens",
        0,
    ),
    "gateway_ml.ai_provider_deepseek": (
        {"thinking": {"type": "disabled"}},
        "max_tokens",
        0,
    ),
    "gateway_ml.ai_provider_moonshot": ({"temperature": 1}, "max_tokens", 2000),
    "gateway_ml.ai_provider_anthropic": ({}, "max_tokens", 0),
}


@tagged("post_install", "-at_install")
class TestProviderServicesSendWhatTheModuleSent(TransactionCase):
    def _composed(self, xmlid, operation):
        row = self.env.ref(xmlid)._service_for(operation)
        return (
            f"{row.service_id.endpoint_url}{row.path}",
            row.wire,
            row.model_id.code,
            row.timeout,
        )

    def test_every_chat_operation_composes_the_request_it_always_sent(self):
        for xmlid, expected in CHAT.items():
            with self.subTest(provider=xmlid):
                self.assertEqual(self._composed(xmlid, "chat"), expected)

    def test_every_transcription_composes_the_request_it_always_sent(self):
        for xmlid, expected in TRANSCRIBE.items():
            with self.subTest(provider=xmlid):
                self.assertEqual(self._composed(xmlid, "transcribe"), expected)

    def test_every_chat_model_keeps_the_request_shape_it_always_sent(self):
        for xmlid, expected in CHAT_MODEL_SHAPES.items():
            model = self.env.ref(xmlid)._service_for("chat").model_id
            with self.subTest(provider=xmlid):
                self.assertEqual(
                    (
                        model.request_extra or {},
                        model.max_tokens_param,
                        model.min_max_tokens,
                    ),
                    expected,
                )

    def test_the_timed_transcription_runs_on_whisper(self):
        timed = self.env.ref("gateway_ml.ai_provider_openai")._service_for(
            "transcribe_timed"
        )

        self.assertEqual(timed.model_id.code, "whisper-1")
        self.assertTrue(timed.model_id.has_timestamps)

    def test_an_untimed_transcription_model_reads_languages_as_a_list(self):
        rows = self.env["gateway.ml.model"].search(
            [("code", "in", list(UNTIMED_TRANSCRIPTION_MODELS))]
        )

        self.assertTrue(rows)
        self.assertEqual(set(rows.mapped("language_form_key")), {"languages[]"})

    def test_claude_rows_carry_what_each_model_refuses(self):
        refusing = {
            model.code: (model.sampling_params, model.forced_tool_choice)
            for model in self.env["gateway.ml.model"].search(
                [
                    (
                        "provider_id",
                        "=",
                        self.env.ref("gateway_ml.ai_provider_anthropic").id,
                    )
                ]
            )
            if not (model.sampling_params and model.forced_tool_choice)
        }
        self.assertEqual(
            refusing,
            {
                "claude-fable-5-1": (False, False),
                "claude-opus-5": (False, True),
                "claude-sonnet-5": (False, True),
                "claude-fable-5": (False, True),
                "claude-opus-4-8": (False, True),
                "claude-opus-4-7": (False, True),
            },
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
