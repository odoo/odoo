from odoo.tests import TransactionCase, tagged


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
