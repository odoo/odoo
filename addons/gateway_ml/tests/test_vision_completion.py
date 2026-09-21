from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tests.common import credential_for
from odoo.addons.gateway_ml.tools.ai_clients import (
    BaseAIClient,
    ClaudeClient,
    GeminiClient,
    OpenAICompatibleClient,
)
from odoo.addons.integration.tools.exceptions import CommError

_IMAGE = "aGVsbG8="


@tagged("post_install", "-at_install")
class TestVisionCompletion(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for code in ("openai", "groq", "deepseek", "gemini"):
            credential_for(cls.env, code, credential_value="K")

    def test_it_sends_the_image_as_a_data_uri_part(self):
        client = OpenAICompatibleClient(self.env, endpoint_code="openai")
        with patch.object(
            client._client,
            "post",
            return_value={
                "status_code": 200,
                "body": {"choices": [{"message": {"content": "an invoice"}}]},
            },
        ) as post:
            answer = client.complete("what is this?", images=((_IMAGE, "image/png"),))

        self.assertEqual(answer, "an invoice")
        content = post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "what is this?"})
        self.assertEqual(
            content[1]["image_url"]["url"], f"data:image/png;base64,{_IMAGE}"
        )

    def test_a_vendor_with_its_own_vision_model_uses_it(self):
        self.env["gateway.ml.model"].create(
            {
                "provider_id": self.env.ref("gateway_ml.ai_provider_groq").id,
                "name": "See Model",
                "code": "see-model",
                "kind": "vision",
                "has_vision": True,
            }
        )
        client = OpenAICompatibleClient(self.env, endpoint_code="groq")
        with patch.object(
            client._client,
            "post",
            return_value={
                "status_code": 200,
                "body": {"choices": [{"message": {"content": "ok"}}]},
            },
        ) as post:
            client.complete("what is this?", images=((_IMAGE, "image/png"),))

        self.assertEqual(post.call_args.kwargs["json"]["model"], "see-model")

    def test_groq_reads_no_images_since_scout_shut_down(self):
        with self.assertRaises(CommError) as caught:
            OpenAICompatibleClient(self.env, endpoint_code="groq").complete(
                "what is this?", images=((_IMAGE, "image/png"),)
            )
        self.assertIn("no images", str(caught.exception))

    def test_a_truncated_answer_is_refused_rather_than_returned(self):
        client = OpenAICompatibleClient(self.env, endpoint_code="openai")
        with patch.object(
            client._client,
            "post",
            return_value={
                "status_code": 200,
                "body": {
                    "choices": [
                        {"message": {"content": "partial"}, "finish_reason": "length"}
                    ]
                },
            },
        ):
            with self.assertRaises(CommError) as caught:
                client.complete("what is this?", images=((_IMAGE, "image/png"),))

        self.assertIn("no usable content", str(caught.exception))

    def test_a_vendor_that_reads_no_images_says_so(self):
        client = OpenAICompatibleClient(self.env, endpoint_code="deepseek")
        with self.assertRaises(CommError) as caught:
            client.complete("what is this?", images=((_IMAGE, "image/png"),))
        self.assertIn("no images", str(caught.exception))

    def test_a_vendor_that_reads_no_images_still_answers_text(self):
        client = OpenAICompatibleClient(self.env, endpoint_code="deepseek")
        body = {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
        with patch.object(
            client._client, "post", return_value={"status_code": 200, "body": body}
        ):
            self.assertEqual(client.complete("what is this?"), "ok")

    def test_gemini_sends_each_image_inline(self):
        client = GeminiClient(self.env)
        body = {"candidates": [{"content": {"parts": [{"text": "a receipt"}]}}]}
        with patch.object(
            client._client, "post", return_value={"status_code": 200, "body": body}
        ) as post:
            answer = client.complete("what is this?", images=((_IMAGE, "image/webp"),))

        self.assertEqual(answer, "a receipt")
        parts = post.call_args.kwargs["json"]["contents"][0]["parts"]
        self.assertEqual(
            parts[1], {"inline_data": {"mime_type": "image/webp", "data": _IMAGE}}
        )

    def test_every_chat_client_implements_complete(self):
        for cls in (OpenAICompatibleClient, GeminiClient, ClaudeClient):
            with self.subTest(client=cls.__name__):
                self.assertIsNot(cls.complete, BaseAIClient.complete)
