import json
from unittest.mock import MagicMock, patch

from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("solar_ai", "post_install", "-at_install")
class TestSolarAiBase(TransactionCase):
    def test_config_params_loaded(self):
        base_url = self.env["ir.config_parameter"].get_param(
            "solar_ai.openrouter_base_url",
        )
        self.assertEqual(base_url, "https://openrouter.ai/api/v1")

    def test_default_model_configured(self):
        model_name = self.env["ir.config_parameter"].get_param("solar_ai.default_model")
        self.assertIsNotNone(model_name)
        self.assertIn("claude", model_name)


@tagged("solar_ai", "post_install", "-at_install")
class TestSolarAiService(TransactionCase):
    def _mock_openrouter_response(self, content):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": content, "role": "assistant"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        return mock_resp

    @patch("httpx.post")
    def test_chat_returns_content(self, mock_post):
        mock_post.return_value = self._mock_openrouter_response("Hello, solar world!")
        self.env["ir.config_parameter"].set_param(
            "solar_ai.openrouter_api_key",
            "test-key-123",
        )

        service = self.env["solar.ai.service"]
        result = service.chat([{"role": "user", "content": "Hello"}])
        self.assertEqual(result["content"], "Hello, solar world!")

    @patch("httpx.post")
    def test_classify_document_returns_code(self, mock_post):
        mock_post.return_value = self._mock_openrouter_response(
            json.dumps(
                {"document_type_code": "bill_electricity", "confidence": 0.95},
            ),
        )
        self.env["ir.config_parameter"].set_param(
            "solar_ai.openrouter_api_key",
            "test-key",
        )

        service = self.env["solar.ai.service"]
        result = service.classify_document_text(
            "Monthly electricity consumption: 850 kWh. Total: 3210 UAH",
        )
        self.assertEqual(result.get("document_type_code"), "bill_electricity")


@tagged("solar_ai", "post_install", "-at_install")
class TestOlgProxy(HttpCase):
    @patch("httpx.post")
    def test_olg_chat_route(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [
                {"message": {"content": "AI response text", "role": "assistant"}}
            ],
            "usage": {},
        }
        self.env["ir.config_parameter"].sudo().set_param(
            "solar_ai.openrouter_api_key",
            "test-key",
        )
        self.authenticate("admin", "admin")

        resp = self.url_open(
            "/solar_ai/olg/api/olg/1/chat",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "id": 1,
                    "params": {"prompt": "Translate this", "conversation_history": []},
                },
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.json()
        self.assertEqual(result.get("result", {}).get("status"), "success")
