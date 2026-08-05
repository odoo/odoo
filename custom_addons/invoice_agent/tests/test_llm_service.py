from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestLLMService(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param(
            "invoice_agent.anthropic_api_key", "sk-test-key-123"
        )
        self.llm_service = self.env["invoice.llm.service"]

    @patch("anthropic.Anthropic")
    def test_call_claude_success(self, mock_anthropic_class):
        # إعداد الـ Mock Response
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"vendor": "Acme Corp"}')]
        mock_response.usage.input_tokens = 150
        mock_response.usage.output_tokens = 50
        mock_response.stop_reason = "end_turn"

        mock_client.messages.create.return_value = mock_response

        # التنفيذ
        res = self.llm_service.call_claude(
            system_prompt="Extract data",
            messages=[{"role": "user", "content": "Sample Invoice"}],
        )

        # التأكد من صحة النتائج وقيم المداخلات
        self.assertEqual(res["content"], '{"vendor": "Acme Corp"}')
        mock_client.messages.create.assert_called_once_with(
            model="claude-opus-4-8",
            max_tokens=1000,
            system="Extract data",
            messages=[{"role": "user", "content": "Sample Invoice"}],
        )

    def test_missing_api_key_raises_user_error(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "invoice_agent.anthropic_api_key", ""
        )
        with self.assertRaises(UserError):
            self.llm_service.call_claude(system_prompt="", messages=[])
