from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tests.common import connect, disconnect
from odoo.addons.gateway_ml.tools import ProviderAssistant
from odoo.addons.gateway_ml.tools.assistant_adoption import (
    adopt_assistant_columns,
    chat_model_for_code,
    connect_credential,
)
from odoo.addons.integration.tools import CommError

_CLIENT_FACTORY = "odoo.addons.gateway_ml.tools.provider_assistant.get_api_client"

_CHAT_REPLY = {
    "status_code": 200,
    "body": {
        "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
        "content": [{"type": "text", "text": "{}"}],
        "stop_reason": "end_turn",
    },
    "text": "{}",
}

VENDORS = ("groq", "google", "openai", "deepseek", "moonshot", "anthropic")


@tagged("post_install", "-at_install")
class TestProviderAssistant(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.providers = {
            code: cls.env.ref(f"gateway_ml.ai_provider_{code}") for code in VENDORS
        }
        for provider in cls.providers.values():
            connect(cls.env, provider)

    def _assistant(self, code, model=None):
        return self.providers[code]._assistant(model=model)

    def _sent(self, code, max_tokens=600, temperature=0.1, images=None, model=None):
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = _CHAT_REPLY
            self._assistant(code, model=model).chat_json(
                "sys", "user", max_tokens, temperature, images=images
            )
        return factory

    def _sent_body(self, code, **kwargs):
        return self._sent(code, **kwargs).return_value.post.call_args.kwargs["json"]

    def test_every_vendor_is_configured_once_connected(self):
        for code in VENDORS:
            with self.subTest(vendor=code):
                self.assertTrue(self._assistant(code).configured)

    def test_a_vendor_the_company_is_not_connected_to_is_not_configured(self):
        self.env["integration.connection"].search(
            [("service_id", "in", self.providers["groq"].service_ids.service_id.ids)]
        ).action_archive()
        assistant = self._assistant("groq")
        self.assertFalse(assistant.configured)
        with patch(_CLIENT_FACTORY) as factory:
            self.assertIsNone(assistant.chat_json("sys", "user", 10, 0.1))
        factory.assert_not_called()

    def test_no_provider_is_not_configured(self):
        assistant = ProviderAssistant(self.env["gateway.ml.provider"])
        self.assertFalse(assistant.configured)
        self.assertFalse(assistant.supports_audio)
        self.assertIsNone(assistant.chat_json("sys", "user", 10, 0.1))

    def test_the_chat_operation_default_model_applies(self):
        groq = self.providers["groq"]
        self.assertEqual(
            self._assistant("groq").model, groq._service_for("chat").model_id.code
        )

    def test_a_model_row_overrides_the_default(self):
        other = chat_model_for_code(self.providers["groq"], "other-model")
        self.assertEqual(self._assistant("groq", model=other).model, "other-model")
        self.assertEqual(self._sent_body("groq", model=other)["model"], "other-model")

    def test_the_token_floor_of_the_model_row_reaches_the_sent_body(self):
        self.assertEqual(
            self._sent_body("moonshot", max_tokens=600)["max_tokens"], 2000
        )
        self.assertEqual(
            self._sent_body("moonshot", max_tokens=4000)["max_tokens"], 4000
        )
        self.assertEqual(self._sent_body("groq", max_tokens=600)["max_tokens"], 600)

    def test_the_model_rows_request_extra_overrides_the_caller(self):
        self.assertEqual(
            self._sent_body("moonshot", temperature=0.1)["temperature"],
            1,
            "Kimi rejects any other temperature, so the model row must win over "
            "the 0.1 the caller asked for.",
        )
        self.assertEqual(self._sent_body("groq", temperature=0.1)["temperature"], 0.1)

    def test_openai_caps_output_under_the_name_its_reasoning_models_accept(self):
        sent = self._sent_body("openai", max_tokens=600)
        self.assertEqual(sent["max_completion_tokens"], 600)
        self.assertNotIn("max_tokens", sent)
        self.assertEqual(sent["reasoning_effort"], "none")

    def test_deepseek_chat_runs_without_thinking(self):
        self.assertEqual(self._sent_body("deepseek")["thinking"], {"type": "disabled"})

    def test_claude_is_sent_no_sampling_parameter(self):
        self.assertNotIn("temperature", self._sent_body("anthropic"))

    def test_the_call_rides_the_chat_operations_service_and_path(self):
        for code in VENDORS:
            with self.subTest(vendor=code):
                factory = self._sent(code)
                chat = self.providers[code]._service_for("chat")
                self.assertEqual(factory.call_args.args[1], chat.service_id.code)
                post = factory.return_value.post.call_args
                self.assertEqual(post.args[0], chat.path)
                self.assertEqual(post.kwargs["timeout"], chat.timeout)

    def test_audio_capability_follows_the_transcribe_operation(self):
        self.assertTrue(self._assistant("groq").supports_audio)
        self.assertTrue(self._assistant("google").supports_audio)
        self.assertTrue(self._assistant("openai").supports_audio)
        self.assertFalse(self._assistant("anthropic").supports_audio)
        self.assertFalse(self._assistant("deepseek").supports_audio)
        self.assertFalse(self._assistant("moonshot").supports_audio)

    def test_vision_capability_follows_the_chosen_model_row(self):
        self.assertFalse(self._assistant("groq").supports_vision)
        self.assertTrue(self._assistant("google").supports_vision)
        self.assertTrue(self._assistant("openai").supports_vision)
        self.assertTrue(self._assistant("anthropic").supports_vision)
        self.assertFalse(self._assistant("deepseek").supports_vision)
        self.assertFalse(self._assistant("moonshot").supports_vision)

    def test_openai_wire_image_payload_shape(self):
        body = self._sent_body("openai", images=[("QUJD", "image/png")])
        content = body["messages"][1]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "user"})
        self.assertEqual(
            content[1],
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}},
        )

    def test_anthropic_wire_image_payload_shape(self):
        body = self._sent_body("anthropic", images=[("QUJD", "image/png")])
        content = body["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "user"})
        self.assertEqual(
            content[1],
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": "QUJD"},
            },
        )

    def test_images_dropped_when_the_model_cannot_read_them(self):
        with self.assertLogs(
            "odoo.addons.gateway_ml.tools.provider_assistant", level="WARNING"
        ) as logs:
            body = self._sent_body("deepseek", images=[("QUJD", "image/png")])
        self.assertEqual(body["messages"][1]["content"], "user")
        self.assertTrue(any("cannot read images" in line for line in logs.output))

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
            transcript = self._assistant("google").transcribe(b"audio", "voice.oga")
        self.assertEqual(transcript, "Compra de tres llantas, doce mil pesos.")
        transcribe = self.providers["google"]._service_for("transcribe")
        self.assertEqual(factory.call_args.args[1], transcribe.service_id.code)
        self.assertEqual(
            factory.return_value.post.call_args.args[0],
            transcribe.path.format(model=transcribe.model_id.code),
        )
        self.assertEqual(
            factory.return_value.post.call_args.kwargs["timeout"], transcribe.timeout
        )

    def test_gemini_names_no_language_it_was_not_given(self):
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = {
                "status_code": 200,
                "body": {"candidates": [{"content": {"parts": [{"text": "hola"}]}}]},
                "text": "",
            }
            self._assistant("google").transcribe(b"a", "v.ogg")
        instruction = factory.return_value.post.call_args.kwargs["json"]["contents"][0][
            "parts"
        ][0]["text"]
        self.assertNotIn("None", instruction)
        self.assertNotIn("idioma", instruction)

    def test_whisper_transcription_sends_the_operations_model(self):
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = {
                "status_code": 200,
                "body": "hola",
                "text": "hola",
            }
            transcript = self._assistant("groq").transcribe(
                b"a", "v.ogg", language="es"
            )
        self.assertEqual(transcript, "hola")
        transcribe = self.providers["groq"]._service_for("transcribe")
        sent = factory.return_value.post.call_args.kwargs
        self.assertEqual(sent["data"]["model"], transcribe.model_id.code)
        self.assertEqual(sent["files"]["file"][0], "v.ogg")

    def test_transcribe_refused_without_audio_support(self):
        with patch(_CLIENT_FACTORY) as factory:
            self.assertIsNone(self._assistant("anthropic").transcribe(b"a", "v.ogg"))
        factory.assert_not_called()

    def test_a_failed_exchange_returns_none_rather_than_raising(self):
        with patch(_CLIENT_FACTORY) as factory:
            factory.return_value.post.return_value = {
                "status_code": 401,
                "body": {"error": "bad key"},
                "text": '{"error": "bad key"}',
            }
            self.assertIsNone(
                self._assistant("groq").chat_json("sys", "user", 600, 0.1)
            )

    def test_transport_errors_fail_soft(self):
        with patch(_CLIENT_FACTORY, side_effect=CommError("no such service")):
            self.assertIsNone(
                self._assistant("groq").chat_json("sys", "user", 600, 0.1)
            )

    def test_an_archived_service_fails_soft(self):
        self.providers["groq"]._service_for("chat").service_id.active = False
        self.assertIsNone(self._assistant("groq").chat_json("sys", "user", 600, 0.1))

    def test_the_company_connection_authenticates_the_call(self):
        for code, header, value in (
            ("anthropic", "x-api-key", "the-key"),
            ("groq", "Authorization", "Bearer the-key"),
        ):
            with self.subTest(vendor=code):
                service = self.providers[code]._service_for("chat").service_id
                connection = self.env["integration.connection"]._resolve(service)
                headers = connection._get_auth_headers()
                self.assertEqual(headers.get(header), value)
                self.assertEqual(len(headers), 1)

    def test_a_webhook_user_reaches_the_companys_connection(self):
        public = self.env(user=self.env.ref("base.public_user"))
        provider = self.providers["groq"].with_env(public)
        self.assertTrue(provider._assistant().configured)


@tagged("post_install", "-at_install")
class TestAssistantAdoption(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.groq = cls.env.ref("gateway_ml.ai_provider_groq")
        cls.google = cls.env.ref("gateway_ml.ai_provider_google")
        cls.category = cls.env.ref("credential.credential_category_api_key")
        disconnect(cls.env, cls.groq)
        disconnect(cls.env, cls.google)

    def _loose_key(self, name="Bot AI key"):
        return self.env["credential.credential"].create(
            {
                "name": name,
                "category_id": self.category.id,
                "company_id": self.env.company.id,
                "api_key": "sk-bot",
            }
        )

    def _connected_credentials(self, provider):
        return {
            service.code: self.env["integration.connection"]
            ._resolve(service)
            .credential_id
            for service in provider.service_ids.service_id
        }

    def test_an_unknown_model_code_becomes_a_row_with_the_defaults_vision(self):
        row = chat_model_for_code(self.google, "gemini-next")
        self.assertEqual(row.provider_id, self.google)
        self.assertEqual(row.kind, "chat")
        self.assertTrue(row.has_vision)
        self.assertEqual(chat_model_for_code(self.google, "gemini-next"), row)
        self.assertFalse(chat_model_for_code(self.google, " "))

    def test_a_loose_key_connects_every_service_the_vendor_rides(self):
        credential = self._loose_key()
        connect_credential(self.env, self.google, credential, "Bot")
        connected = self._connected_credentials(self.google)
        self.assertEqual(len(connected), 2)
        self.assertEqual(set(connected.values()), {credential})

    def test_an_existing_company_connection_is_kept(self):
        connect(self.env, self.groq, key="company-key")
        before = self._connected_credentials(self.groq)
        with self.assertLogs(
            "odoo.addons.gateway_ml.tools.assistant_adoption", "WARNING"
        ):
            connect_credential(self.env, self.groq, self._loose_key(), "Bot")
        self.assertEqual(self._connected_credentials(self.groq), before)

    def test_a_key_bound_elsewhere_connects_nothing(self):
        credential = self._loose_key()
        credential.endpoint_id = self.env["integration.service"].search(
            [("code", "=", "openai")], limit=1
        )
        with self.assertLogs(
            "odoo.addons.gateway_ml.tools.assistant_adoption", "WARNING"
        ):
            connect_credential(self.env, self.groq, credential, "Bot")
        self.assertFalse(any(self._connected_credentials(self.groq).values()))

    def test_absent_columns_adopt_nothing(self):
        adopt_assistant_columns(self.env, "res.partner", "nothing")
