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
                {"message": {"content": "AI response text", "role": "assistant"}},
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


@tagged("solar_ai", "post_install", "-at_install")
class TestAutoClassify(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "solar_ai.openrouter_api_key",
            "test-key",
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Classify Test Project"},
        )

    @patch("httpx.post")
    def test_auto_classify_on_attachment(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"document_type_code": "bill_electricity", "confidence": 0.92}',
                        "role": "assistant",
                    },
                },
            ],
            "usage": {},
        }
        seed_type = self.env["solar.document.type"].search([], limit=1)
        doc = self.env["solar.document"].create(
            {
                "name": "Test bill",
                "project_id": self.project.id,
                "document_type_id": seed_type.id,
            },
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "electricity_bill_jan.pdf",
                "res_model": "solar.document",
                "res_id": doc.id,
                "mimetype": "application/pdf",
                "datas": b"TW9udGhseSBlbGVjdHJpY2l0eTogODUwIGtXaA==",  # base64
            },
        )
        doc.attachment_id = attachment
        doc._run_ai_classify()
        self.assertTrue(doc.ai_classified)
        self.assertEqual(doc.document_type_id.code, "bill_electricity")


@tagged("solar_ai", "post_install", "-at_install")
class TestConsistencyCheck(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "solar_ai.openrouter_api_key",
            "test-key",
        )
        cls.project = cls.env["project.project"].create({"name": "Consistency Test"})
        doc_type = cls.env.ref("solar_project.solar_dtype_roof_measurement")
        for i in range(2):
            cls.env["solar.document"].create(
                {
                    "name": f"Doc {i}",
                    "project_id": cls.project.id,
                    "document_type_id": doc_type.id,
                },
            )

    @patch("httpx.post")
    def test_consistency_check_creates_activity(self, mock_post):
        inconsistency_response = json.dumps(
            {
                "inconsistencies": [
                    {
                        "severity": "warning",
                        "description": "Roof area in measurement doc (120m²) differs from site plan (95m²)",
                    },
                ],
            },
        )
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [
                {"message": {"content": inconsistency_response, "role": "assistant"}},
            ],
            "usage": {},
        }

        initial_activity_count = len(self.project.activity_ids)
        self.project.action_run_consistency_check()
        self.assertGreater(len(self.project.activity_ids), initial_activity_count)
