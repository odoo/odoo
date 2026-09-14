from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.api_ai.tools import (
    PROVIDERS,
    CatalogAIClient,
    ClaudeClient,
    provider_selection,
    read_anthropic_content,
    read_openai_content,
)
from odoo.addons.integration.tools import CommError

_CLIENT_FACTORY = "odoo.addons.api_ai.tools.catalog_client.get_api_client"


def _with_dedicated_vision_model():
    return patch.dict(
        PROVIDERS,
        {"groq": {**PROVIDERS["groq"], "vision": True, "vision_model": "see-model"}},
    )


class TestCatalogAIClient(TransactionCase):
    def test_selection_matches_catalog(self):
        self.assertEqual(set(dict(provider_selection())), set(PROVIDERS))

    def test_unknown_provider_is_not_configured(self):
        provider = CatalogAIClient("nope", "some-key", env=self.env)
        self.assertFalse(provider.configured)
        self.assertFalse(provider.supports_audio)
        self.assertIsNone(provider.chat_json("sys", "user", 10, 0.1))

    def test_missing_key_is_not_configured(self):
        self.assertFalse(CatalogAIClient("groq", "", env=self.env).configured)

    def test_vendor_default_model_applies(self):
        self.assertEqual(
            CatalogAIClient("groq", "key", env=self.env).model,
            PROVIDERS["groq"]["chat_model"],
        )

    def test_model_override_wins(self):
        self.assertEqual(
            CatalogAIClient("groq", "key", "other-model", env=self.env).model,
            "other-model",
        )

    def test_every_vendor_ships_a_default_model(self):
        for code in PROVIDERS:
            self.assertTrue(
                CatalogAIClient(code, "key", env=self.env).configured,
                f"Vendor {code} must ship a default model.",
            )

    def test_token_budget_floor_applies(self):
        self.assertEqual(
            CatalogAIClient("moonshot", "key", env=self.env)._token_budget(600), 2000
        )
        self.assertEqual(
            CatalogAIClient("moonshot", "key", env=self.env)._token_budget(4000), 4000
        )
        self.assertEqual(
            CatalogAIClient("groq", "key", env=self.env)._token_budget(600), 600
        )

    def _sent_body(self, provider_code, max_tokens=600, temperature=0.1, images=None):
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = {
                "status_code": 200,
                "body": {
                    "choices": [
                        {"message": {"content": "{}"}, "finish_reason": "stop"}
                    ],
                    "content": [{"type": "text", "text": "{}"}],
                },
                "text": "{}",
            }
            CatalogAIClient(provider_code, "key", env=self.env).chat_json(
                "sys", "user", max_tokens, temperature, images=images
            )
        return factory.return_value.post.call_args.kwargs["json"]

    def test_vendor_extra_overrides_caller_in_sent_body(self):
        self.assertEqual(
            self._sent_body("moonshot", temperature=0.1)["temperature"],
            1,
            "Kimi rejects any other temperature, so the vendor must win over "
            "the 0.1 the caller asked for.",
        )
        self.assertEqual(
            self._sent_body("groq", temperature=0.1)["temperature"],
            0.1,
            "A vendor without an override must not alter the caller's value.",
        )

    def test_token_floor_reaches_the_sent_body(self):
        self.assertEqual(
            self._sent_body("moonshot", max_tokens=600)["max_tokens"],
            2000,
            "Without the floor the model spends the budget thinking and "
            "returns empty content.",
        )
        self.assertEqual(
            self._sent_body("groq", max_tokens=600)["max_tokens"],
            600,
            "A vendor without a floor must keep the caller's cap.",
        )

    def test_openai_caps_output_under_the_name_its_reasoning_models_accept(self):
        sent = self._sent_body("openai", max_tokens=600)
        self.assertEqual(sent["max_completion_tokens"], 600)
        self.assertNotIn("max_tokens", sent)
        self.assertEqual(sent["reasoning_effort"], "none")

    def test_deepseek_chat_runs_without_thinking(self):
        self.assertEqual(
            self._sent_body("deepseek")["thinking"],
            {"type": "disabled"},
            "deepseek-flash thinks by default, and in thinking mode a named "
            "tool_choice is a 400",
        )

    def test_audio_capability_per_vendor(self):
        self.assertTrue(CatalogAIClient("groq", "key", env=self.env).supports_audio)
        self.assertTrue(CatalogAIClient("gemini", "key", env=self.env).supports_audio)
        self.assertFalse(CatalogAIClient("claude", "key", env=self.env).supports_audio)
        self.assertFalse(
            CatalogAIClient("deepseek", "key", env=self.env).supports_audio
        )

    def test_transcribe_excludes_thinking_parts(self):
        payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Debo transcribir literalmente…", "thought": True},
                            {"text": "Compra de tres llantas, doce mil pesos."},
                        ]
                    }
                }
            ]
        }
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = {
                "status_code": 200,
                "body": payload,
                "text": "",
            }
            transcript = CatalogAIClient("gemini", "key", env=self.env).transcribe(
                b"audio", "voice.oga"
            )
        self.assertEqual(transcript, "Compra de tres llantas, doce mil pesos.")

    def test_gemini_names_no_language_it_was_not_given(self):
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = {
                "status_code": 200,
                "body": {"candidates": [{"content": {"parts": [{"text": "hola"}]}}]},
                "text": "",
            }
            CatalogAIClient("gemini", "key", env=self.env).transcribe(b"a", "v.ogg")
        instruction = factory.return_value.post.call_args.kwargs["json"]["contents"][0][
            "parts"
        ][0]["text"]
        self.assertNotIn("None", instruction)
        self.assertNotIn("idioma", instruction)

    def test_audio_timeout_per_vendor(self):
        self.assertEqual(
            CatalogAIClient("gemini", "key", env=self.env)._audio_timeout, 90
        )
        self.assertEqual(
            CatalogAIClient("groq", "key", env=self.env)._audio_timeout,
            30,
            "A vendor without an override keeps the shared default.",
        )

    def test_transcribe_refused_without_audio_support(self):
        with patch(_CLIENT_FACTORY) as factory:
            result = CatalogAIClient("claude", "key", env=self.env).transcribe(
                b"audio", "voice.ogg"
            )
        self.assertIsNone(result)
        factory.assert_not_called()

    def test_vision_capability_per_vendor(self):
        self.assertFalse(
            CatalogAIClient("groq", "key", env=self.env).supports_vision,
            "Groq shut Llama 4 Scout down and serves no production vision model",
        )
        self.assertTrue(CatalogAIClient("gemini", "key", env=self.env).supports_vision)
        self.assertTrue(CatalogAIClient("openai", "key", env=self.env).supports_vision)
        self.assertTrue(CatalogAIClient("claude", "key", env=self.env).supports_vision)
        self.assertFalse(
            CatalogAIClient("deepseek", "key", env=self.env).supports_vision
        )
        self.assertFalse(
            CatalogAIClient("moonshot", "key", env=self.env).supports_vision
        )

    def test_a_dedicated_vision_model_differs_from_text_model(self):
        with _with_dedicated_vision_model():
            provider = CatalogAIClient("groq", "key", env=self.env)
        self.assertNotEqual(provider.vision_model, provider.model)
        self.assertEqual(provider.vision_model, "see-model")

    def test_vendor_default_vision_model_applies(self):
        for code in ("gemini", "openai", "claude"):
            provider = CatalogAIClient(code, "key", env=self.env)
            self.assertEqual(
                provider.vision_model,
                provider.model,
                f"Vendor {code} ships no dedicated vision model.",
            )

    def test_vision_model_override_reaches_a_shared_model_vendor(self):
        self.assertEqual(
            CatalogAIClient("openai", "key", "custom").vision_model, "custom"
        )
        with _with_dedicated_vision_model():
            self.assertEqual(
                CatalogAIClient("groq", "key", "custom").vision_model,
                "see-model",
                "Overriding the model names the text one; pointing vision at it "
                "would blind the call.",
            )

    def test_openai_wire_image_payload_shape(self):
        with _with_dedicated_vision_model():
            body = self._sent_body("groq", images=[("QUJD", "image/png")])
        content = body["messages"][1]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "user"})
        self.assertEqual(
            content[1],
            {
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64,QUJD"},
            },
        )
        self.assertEqual(
            body["model"],
            "see-model",
            "An image-carrying call must use the vision model.",
        )

    def test_anthropic_wire_image_payload_shape(self):
        body = self._sent_body("claude", images=[("QUJD", "image/png")])
        content = body["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "user"})
        self.assertEqual(
            content[1],
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": "QUJD",
                },
            },
        )

    def test_images_dropped_when_unsupported(self):
        with self.assertLogs(
            "odoo.addons.api_ai.tools.catalog_client", level="WARNING"
        ) as logs:
            body = self._sent_body("deepseek", images=[("QUJD", "image/png")])
        self.assertEqual(
            body["messages"][1]["content"],
            "user",
            "Dropping the image must leave the plain text prompt, not a parts list.",
        )
        self.assertEqual(body["model"], PROVIDERS["deepseek"]["chat_model"])
        self.assertTrue(any("cannot read images" in line for line in logs.output))

    def test_no_images_body_unchanged(self):
        body = self._sent_body("groq")
        self.assertEqual(body["messages"][1]["content"], "user")
        self.assertEqual(body["model"], PROVIDERS["groq"]["chat_model"])

    def test_every_wire_names_a_seeded_service(self):
        outbound = self.env["integration.service"]
        for code, spec in PROVIDERS.items():
            for key in ("chat_service", "audio_service"):
                endpoint_code = spec.get(key)
                if not endpoint_code:
                    continue
                self.assertTrue(
                    outbound.search_count([("code", "=", endpoint_code)]),
                    f"{code}.{key} names {endpoint_code!r}, which no "
                    f"integration.service record declares",
                )

    def test_gemini_chat_and_audio_ride_different_services(self):
        gemini = PROVIDERS["gemini"]
        self.assertNotEqual(gemini["chat_service"], gemini["audio_service"])

    def test_no_catalog_entry_carries_a_full_url(self):
        for code, spec in PROVIDERS.items():
            for key, value in spec.items():
                if isinstance(value, str) and value.startswith("http"):
                    self.fail(
                        f"{code}.{key} carries a full URL ({value}); the base "
                        f"belongs to the integration.service record and only "
                        f"the path belongs here"
                    )

    def test_a_failed_exchange_returns_none_rather_than_raising(self):
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = {
                "status_code": 401,
                "body": {"error": "bad key"},
                "text": '{"error": "bad key"}',
            }
            result = CatalogAIClient("groq", "key", env=self.env).chat_json(
                "sys", "user", 600, 0.1
            )
        self.assertIsNone(result)

    def test_transport_errors_fail_soft(self):
        with patch(_CLIENT_FACTORY, side_effect=CommError("no such service")):
            result = CatalogAIClient("groq", "key", env=self.env).chat_json(
                "sys", "user", 600, 0.1
            )
        self.assertIsNone(result)

    def test_an_archived_endpoint_fails_soft_like_any_transport_error(self):
        self.env["integration.service"].search([("code", "=", "groq")]).active = False
        result = CatalogAIClient("groq", "key", env=self.env).chat_json(
            "sys", "user", 600, 0.1
        )
        self.assertIsNone(result)

    def test_the_bot_credential_is_handed_to_the_transport(self):
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = {
                "status_code": 200,
                "body": {
                    "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]
                },
                "text": "{}",
            }
            CatalogAIClient("groq", "key", env=self.env, credential_id=42).chat_json(
                "sys", "user", 600, 0.1
            )
        self.assertEqual(factory.call_args.kwargs["credential_id"], 42)

    def test_without_an_environment_the_provider_is_unusable(self):
        provider = CatalogAIClient("groq", "key")
        self.assertFalse(provider.configured)
        self.assertIsNone(provider.chat_json("sys", "user", 600, 0.1))

    def test_composed_urls_match_what_the_module_sent_before_the_transport(self):
        expected = {
            ("groq", "chat"): "https://api.groq.com/openai/v1/chat/completions",
            ("groq", "audio"): "https://api.groq.com/openai/v1/audio/transcriptions",
            ("gemini", "chat"): (
                "https://generativelanguage.googleapis.com"
                "/v1beta/openai/chat/completions"
            ),
            ("gemini", "audio"): (
                "https://generativelanguage.googleapis.com"
                "/v1beta/models/{model}:generateContent"
            ),
            ("openai", "chat"): "https://api.openai.com/v1/chat/completions",
            ("openai", "audio"): "https://api.openai.com/v1/audio/transcriptions",
            ("deepseek", "chat"): "https://api.deepseek.com/v1/chat/completions",
            ("moonshot", "chat"): "https://api.moonshot.ai/v1/chat/completions",
            ("claude", "chat"): "https://api.anthropic.com/v1/messages",
        }
        outbound = self.env["integration.service"]
        composed = {}
        for code, spec in PROVIDERS.items():
            for kind in ("chat", "audio"):
                endpoint_code = spec.get(f"{kind}_service")
                if not endpoint_code:
                    continue
                service = outbound.search([("code", "=", endpoint_code)], limit=1)
                composed[(code, kind)] = f"{service.endpoint_url}{spec[f'{kind}_path']}"
        self.assertEqual(composed, expected)


class TestSharedResponseReaders(TransactionCase):
    def test_anthropic_reader_joins_every_text_block(self):
        text, problem = read_anthropic_content(
            {
                "content": [
                    {"type": "text", "text": "one "},
                    {"type": "text", "text": "two"},
                ],
                "stop_reason": "end_turn",
            }
        )
        self.assertIsNone(problem)
        self.assertEqual(text, "one two")

    def test_anthropic_reader_survives_a_leading_thinking_block(self):
        text, problem = read_anthropic_content(
            {
                "content": [
                    {"type": "thinking", "thinking": "let me consider"},
                    {"type": "text", "text": "the answer"},
                ],
                "stop_reason": "end_turn",
            }
        )
        self.assertIsNone(problem)
        self.assertEqual(text, "the answer")

    def test_anthropic_reader_refuses_a_truncated_answer(self):
        text, problem = read_anthropic_content(
            {
                "content": [{"type": "text", "text": '{"partial"'}],
                "stop_reason": "max_tokens",
            }
        )
        self.assertEqual(text, "")
        self.assertIn("truncated", problem)

    def test_openai_reader_refuses_a_truncated_answer(self):
        text, problem = read_openai_content(
            {
                "choices": [
                    {"message": {"content": '{"partial"'}, "finish_reason": "length"}
                ]
            }
        )
        self.assertEqual(text, "")
        self.assertIn("truncated", problem)

    def test_openai_reader_accepts_a_finished_answer(self):
        text, problem = read_openai_content(
            {"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]}
        )
        self.assertIsNone(problem)
        self.assertEqual(text, "done")

    def test_readers_refuse_a_non_dict_payload(self):
        for reader in (read_openai_content, read_anthropic_content):
            with self.subTest(reader=reader.__name__):
                text, problem = reader("not a dict")
                self.assertEqual(text, "")
                self.assertIn("JSON object", problem)

    def test_the_class_stack_reads_a_thinking_first_response(self):
        client = ClaudeClient.__new__(ClaudeClient)
        self.assertEqual(
            client._extract_text_from_response(
                {
                    "content": [
                        {"type": "thinking", "thinking": "…"},
                        {"type": "text", "text": "the answer"},
                    ],
                    "stop_reason": "end_turn",
                }
            ),
            "the answer",
        )

    def test_the_class_stack_refuses_a_truncated_response(self):
        client = ClaudeClient.__new__(ClaudeClient)
        with self.assertRaises(CommError) as caught:
            client._extract_text_from_response(
                {
                    "content": [{"type": "text", "text": "half"}],
                    "stop_reason": "max_tokens",
                }
            )
        self.assertIn("truncated", str(caught.exception))


class TestAuthHeadersComeFromTheEndpoint(TransactionCase):
    def _sent_headers(self, provider_code):
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = {
                "status_code": 200,
                "body": {
                    "choices": [
                        {"message": {"content": "{}"}, "finish_reason": "stop"}
                    ],
                    "content": [{"type": "text", "text": "{}"}],
                    "stop_reason": "end_turn",
                },
                "text": "{}",
            }
            CatalogAIClient(provider_code, "the-key", env=self.env).chat_json(
                "sys", "user", 600, 0.1
            )
        return factory.return_value.post.call_args.kwargs["headers"]

    def test_anthropic_gets_its_own_key_header(self):
        headers = self._sent_headers("claude")
        self.assertEqual(headers.get("x-api-key"), "the-key")
        self.assertNotIn("Authorization", headers)

    def test_a_bearer_endpoint_gets_authorization_alone(self):
        headers = self._sent_headers("groq")
        self.assertEqual(headers.get("Authorization"), "Bearer the-key")
        self.assertNotIn("X-API-Key", headers)

    def test_the_version_header_is_not_built_here(self):
        self.assertNotIn("anthropic-version", self._sent_headers("claude"))

    def test_an_unseeded_endpoint_yields_no_auth_rather_than_raising(self):
        endpoint = self.env["integration.service"].search(
            [("code", "=", "claude")], limit=1
        )
        self.assertTrue(endpoint)
        self.assertEqual(endpoint._api_key_headers(""), {})
