import math
from unittest.mock import Mock, patch

from odoo.tests.common import TransactionCase

from odoo.addons.gateway_ml.tests.common import credential_for
from odoo.addons.gateway_ml.tools.ai_clients import get_ai_client
from odoo.addons.integration.tools.exceptions import CommError


class TestOpenAICompatibleClient(TransactionCase):
    def setUp(self):
        super().setUp()

        self.credential = credential_for(
            self.env, "deepseek", credential_value="test_token_123"
        )

    def test_validate_params_temperature_valid(self):
        client = get_ai_client(self.env, "deepseek")

        client._check_params(temperature=0.0)
        client._check_params(temperature=1.0)
        client._check_params(temperature=2.0)

    def test_validate_params_temperature_invalid(self):
        client = get_ai_client(self.env, "deepseek")

        with self.assertRaises(ValueError):
            client._check_params(temperature=-0.1)

        with self.assertRaises(ValueError):
            client._check_params(temperature=2.1)

        with self.assertRaises(ValueError):
            client._check_params(temperature="not_a_number")

    def test_validate_params_max_tokens_valid(self):
        client = get_ai_client(self.env, "deepseek")

        client._check_params(max_tokens=100)
        client._check_params(max_tokens=4096)

    def test_validate_params_max_tokens_invalid(self):
        client = get_ai_client(self.env, "deepseek")

        with self.assertRaises(ValueError):
            client._check_params(max_tokens=0)

        with self.assertRaises(ValueError):
            client._check_params(max_tokens=-100)

        with self.assertRaises(ValueError):
            client._check_params(max_tokens=math.pi)

    @patch("odoo.addons.gateway_ml.tools.ai_clients.base.get_api_client")
    def test_validate_response_valid_json(self, mock_get_client):
        client = get_ai_client(self.env, "deepseek")

        wrapped_response = {
            "status_code": 200,
            "body": {"status": "success", "data": {}},
            "headers": {},
            "text": "",
            "elapsed_ms": 0,
        }

        result = client._get_response_body(wrapped_response)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "success")

    @patch("odoo.addons.gateway_ml.tools.ai_clients.base.get_api_client")
    def test_validate_response_invalid_json(self, mock_get_client):
        client = get_ai_client(self.env, "deepseek")

        response_no_body = {
            "status_code": 200,
            "headers": {},
            "text": "<html>Error</html>",
        }

        with self.assertRaises(CommError) as cm:
            client._get_response_body(response_no_body)

        self.assertIn("JSON object body", str(cm.exception))

    @patch("odoo.addons.gateway_ml.tools.ai_clients.base.get_api_client")
    def test_chat_completion_calls_validation(self, mock_get_client):
        mock_client_instance = Mock()
        mock_response = Mock(headers={"content-type": "application/json"})
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}]
        }
        mock_client_instance.post.return_value = mock_response
        mock_get_client.return_value = mock_client_instance

        client = get_ai_client(self.env, "deepseek")

        with patch.object(client, "_check_params") as mock_validate:
            with patch.object(
                client, "_get_response_body", return_value=mock_response.json()
            ):
                client.chat_completion(
                    messages=[{"role": "user", "content": "Hello"}],
                    temperature=1.5,
                    max_tokens=100,
                )

                mock_validate.assert_called_once()

    def test_get_usage_returns_token_counts(self):
        client = get_ai_client(self.env, "deepseek")

        response = {
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 2000,
                "total_tokens": 3000,
            },
            "model": "deepseek-flash",
        }

        usage = client.get_usage(response)

        self.assertEqual(usage["prompt_tokens"], 1000)
        self.assertEqual(usage["completion_tokens"], 2000)
        self.assertEqual(usage["total_tokens"], 3000)
        self.assertEqual(usage["model"], "deepseek-flash")
        self.assertNotIn("estimated_cost_usd", usage)

    def test_get_usage_empty_response(self):
        client = get_ai_client(self.env, "deepseek")

        response = {}
        usage = client.get_usage(response)

        self.assertEqual(usage["prompt_tokens"], 0)
        self.assertEqual(usage["completion_tokens"], 0)
        self.assertEqual(usage["total_tokens"], 0)


class TestOpenAICompatibleVision(TransactionCase):
    def setUp(self):
        super().setUp()

        self.credential = credential_for(
            self.env, "deepseek", credential_value="test_token_123"
        )

    @patch("odoo.addons.gateway_ml.tools.ai_clients.base.get_api_client")
    def test_it_refuses_images_from_the_catalog(self, mock_get_client):
        mock_get_client.return_value = Mock()
        client = get_ai_client(self.env, "deepseek")

        with self.assertRaises(CommError) as caught:
            client.vision_completion(
                prompt="What's in this image?",
                image_data="base64_encoded_image_data",
            )

        self.assertIn("no images", str(caught.exception))
        mock_get_client.return_value.post.assert_not_called()
