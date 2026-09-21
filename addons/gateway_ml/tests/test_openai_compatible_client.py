import json
import math
from unittest.mock import Mock, patch

from odoo.tests import tagged
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
            client.complete(
                "What's in this image?",
                images=(("base64_encoded_image_data", "image/jpeg"),),
            )

        self.assertIn("no images", str(caught.exception))
        mock_get_client.return_value.post.assert_not_called()


_SCHEMA = {"type": "object", "properties": {"total": {"type": "number"}}}


@tagged("post_install", "-at_install")
class TestOpenAICompatibleComplete(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        credential_for(cls.env, "openai", bearer_token="K")

    def _sent(self, prompt="q", **kwargs):
        client = get_ai_client(self.env, "openai")
        body = {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
        with patch.object(
            client._client, "post", return_value={"status_code": 200, "body": body}
        ) as post:
            self.assertEqual(
                client.complete(prompt, model="gpt-5.6-luna", **kwargs), "ok"
            )
        return post.call_args.kwargs["json"]

    def test_a_plain_prompt_is_one_user_message(self):
        sent = self._sent()
        self.assertEqual(sent["messages"], [{"role": "user", "content": "q"}])
        self.assertNotIn("response_format", sent)

    def test_the_system_prompt_leads_and_every_image_follows_the_text(self):
        sent = self._sent(
            "compare",
            system="be brief",
            images=(("QUJD", "image/png"), ("REVG", "image/jpeg")),
        )
        self.assertEqual(
            sent["messages"],
            [
                {"role": "system", "content": "be brief"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "compare"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64,QUJD"},
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64,REVG"},
                        },
                    ],
                },
            ],
        )

    def test_json_schema_mode_sends_the_schema_as_the_response_format(self):
        sent = self._sent(response_schema=_SCHEMA, structured_output="json_schema")
        self.assertEqual(
            sent["response_format"],
            {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": _SCHEMA},
            },
        )
        self.assertEqual(sent["messages"], [{"role": "user", "content": "q"}])

    def test_json_object_mode_asks_for_json_and_puts_the_schema_in_the_system(self):
        sent = self._sent(
            system="be brief", response_schema=_SCHEMA, structured_output="json_object"
        )
        self.assertEqual(sent["response_format"], {"type": "json_object"})
        system = sent["messages"][0]
        self.assertEqual(system["role"], "system")
        self.assertTrue(system["content"].startswith("be brief"))
        self.assertIn(json.dumps(_SCHEMA), system["content"])

    def test_prompted_mode_puts_the_schema_in_the_system_alone(self):
        sent = self._sent(response_schema=_SCHEMA, structured_output="prompted")
        self.assertNotIn("response_format", sent)
        self.assertEqual(sent["messages"][0]["role"], "system")
        self.assertIn(json.dumps(_SCHEMA), sent["messages"][0]["content"])
        self.assertEqual(sent["messages"][1], {"role": "user", "content": "q"})
