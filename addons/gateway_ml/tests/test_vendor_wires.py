from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tests.common import credential_for
from odoo.addons.gateway_ml.tools.ai_clients import (
    ClaudeClient,
    GeminiClient,
    OpenAICompatibleClient,
)


def _ok(body):
    return {"status_code": 200, "body": body}


@tagged("post_install", "-at_install")
class TestGeminiWire(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        credential_for(cls.env, "gemini", api_key="K")

    def setUp(self):
        super().setUp()
        self.client = GeminiClient(self.env)

    def test_thinking_parts_are_not_the_answer(self):
        body = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Let me think about this…", "thought": True},
                            {"text": "the "},
                            {"text": "answer"},
                        ]
                    },
                    "finishReason": "STOP",
                }
            ]
        }
        with patch.object(self.client._client, "post", return_value=_ok(body)):
            self.assertEqual(self.client.simple_completion("q"), "the answer")

    def test_a_system_message_is_an_instruction_not_a_model_turn(self):
        body = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        with patch.object(self.client._client, "post", return_value=_ok(body)) as post:
            self.client.chat_completion(
                [
                    {"role": "system", "content": "be terse"},
                    {"role": "user", "content": "hi"},
                    {"role": "assistant", "content": "hello"},
                    {"role": "user", "content": "again"},
                ]
            )
        sent = post.call_args.kwargs["json"]
        self.assertEqual(sent["systemInstruction"], {"parts": [{"text": "be terse"}]})
        self.assertEqual(
            [turn["role"] for turn in sent["contents"]], ["user", "model", "user"]
        )

    def test_the_cap_checked_is_the_resolved_models(self):
        google = self.env["gateway.ml.provider"].search([("code", "=", "gemini")])
        google.default_model_id.max_output_tokens = 100
        body = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        with patch.object(self.client._client, "post", return_value=_ok(body)):
            with self.assertLogs(
                "odoo.addons.gateway_ml.tools.ai_clients.base", "WARNING"
            ):
                self.client.simple_completion("q", max_tokens=500)

    def test_a_small_image_is_still_sent(self):
        body = {"candidates": [{"content": {"parts": [{"text": "a dot"}]}}]}
        with patch.object(self.client._client, "post", return_value=_ok(body)) as post:
            self.client.multimodal_completion("what?", image_data="aGVsbG8=")
        parts = post.call_args.kwargs["json"]["contents"][0]["parts"]
        self.assertEqual(
            parts[1], {"inline_data": {"mime_type": "image/jpeg", "data": "aGVsbG8="}}
        )


@tagged("post_install", "-at_install")
class TestClaudeSampling(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        credential_for(cls.env, "claude", api_key="K")

    def _sent(self, model, **kwargs):
        client = ClaudeClient(self.env)
        body = {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
        with patch.object(client._client, "post", return_value=_ok(body)) as post:
            client.create_message(
                [{"role": "user", "content": "hi"}], model=model, **kwargs
            )
        return post.call_args.kwargs["json"]

    def test_fable_5_1_is_a_known_model(self):
        self.assertIn("claude-fable-5-1", ClaudeClient(self.env)._get_model_rows())

    def test_models_without_sampling_receive_no_sampling_parameter(self):
        for model in ("claude-fable-5-1", "claude-opus-5", "claude-sonnet-5"):
            with self.subTest(model=model):
                sent = self._sent(model, temperature=0.2, top_p=0.9, top_k=5)
                for key in ("temperature", "top_p", "top_k"):
                    self.assertNotIn(key, sent)

    def test_older_models_keep_their_sampling(self):
        sent = self._sent("claude-haiku-4-5", temperature=0.2, top_p=0.9)
        self.assertEqual((sent["temperature"], sent["top_p"]), (0.2, 0.9))

    def test_usage_names_no_model_the_response_did_not(self):
        self.assertEqual(ClaudeClient.get_usage(None, {})["model"], "unknown")


@tagged("post_install", "-at_install")
class TestOpenAIWire(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        credential_for(cls.env, "openai", credential_value="K")

    def test_the_output_cap_goes_under_max_completion_tokens(self):
        client = OpenAICompatibleClient(self.env, endpoint_code="openai")
        body = {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
        with patch.object(client._client, "post", return_value=_ok(body)) as post:
            client.simple_completion("q", max_tokens=500)
        sent = post.call_args.kwargs["json"]
        self.assertEqual(sent["model"], "gpt-5.6-luna")
        self.assertEqual(sent["max_completion_tokens"], 500)
        self.assertNotIn("max_tokens", sent)
        self.assertEqual(sent["reasoning_effort"], "none")

    def test_a_callers_reasoning_effort_wins_over_the_model_row(self):
        client = OpenAICompatibleClient(self.env, endpoint_code="openai")
        body = {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
        with patch.object(client._client, "post", return_value=_ok(body)) as post:
            client.simple_completion("q", reasoning_effort="high")
        self.assertEqual(post.call_args.kwargs["json"]["reasoning_effort"], "high")
