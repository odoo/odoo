from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tests.common import credential_for
from odoo.addons.gateway_ml.tools.ai_clients import ClaudeClient, OpenAICompatibleClient
from odoo.addons.gateway_ml.tools.ai_clients.claude import get_json_output_config
from odoo.addons.integration.tools.exceptions import CommError

_SCHEMA = {
    "type": "object",
    "properties": {
        "total": {"type": "number", "minimum": 0},
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"label": {"type": "string", "maxLength": 80}},
            },
        },
    },
}


def _ok(body):
    return {"status_code": 200, "body": body}


@tagged("post_install", "-at_install")
class TestClaudeStructuredOutput(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        credential_for(cls.env, "claude", api_key="K")

    def setUp(self):
        super().setUp()
        self.client = ClaudeClient(self.env)

    def test_a_model_that_cannot_be_forced_gets_a_json_format_instead(self):
        body = {
            "content": [{"type": "text", "text": '{"total": 12.5, "lines": []}'}],
            "stop_reason": "end_turn",
        }
        with patch.object(self.client._client, "post", return_value=_ok(body)) as post:
            result = self.client.structured_output(
                "read it", _SCHEMA, model="claude-fable-5-1"
            )
        sent = post.call_args.kwargs["json"]
        self.assertEqual(result, {"total": 12.5, "lines": []})
        self.assertNotIn("tool_choice", sent)
        self.assertNotIn("tools", sent)
        self.assertEqual(sent["output_config"]["format"]["type"], "json_schema")

    def test_a_model_that_can_be_forced_still_calls_the_tool(self):
        body = {
            "content": [
                {"type": "tool_use", "name": "extract_data", "input": {"total": 1}}
            ],
            "stop_reason": "tool_use",
        }
        with patch.object(self.client._client, "post", return_value=_ok(body)) as post:
            result = self.client.structured_output(
                "read it", _SCHEMA, model="claude-opus-5"
            )
        self.assertEqual(result, {"total": 1})
        self.assertEqual(
            post.call_args.kwargs["json"]["tool_choice"],
            {"type": "tool", "name": "extract_data"},
        )

    def test_a_forced_tool_choice_is_refused_before_the_wire(self):
        with patch.object(self.client._client, "post") as post:
            with self.assertRaises(ValueError):
                self.client.create_message(
                    [{"role": "user", "content": "hi"}],
                    model="claude-fable-5-1",
                    tool_choice={"type": "any"},
                )
        post.assert_not_called()

    def test_unparseable_json_output_is_a_vendor_failure(self):
        body = {
            "content": [{"type": "text", "text": "not json"}],
            "stop_reason": "end_turn",
        }
        with patch.object(self.client._client, "post", return_value=_ok(body)):
            with self.assertRaises(CommError):
                self.client.structured_output("x", _SCHEMA, model="claude-fable-5-1")

    def test_the_json_format_closes_objects_and_drops_unsupported_constraints(self):
        schema = get_json_output_config(_SCHEMA)["format"]["schema"]
        self.assertIs(schema["additionalProperties"], False)
        self.assertNotIn("minimum", schema["properties"]["total"])
        line = schema["properties"]["lines"]["items"]
        self.assertIs(line["additionalProperties"], False)
        self.assertNotIn("maxLength", line["properties"]["label"])
        self.assertIn("minimum", _SCHEMA["properties"]["total"], "input left intact")

    def test_a_property_named_like_a_keyword_is_still_a_property(self):
        schema = get_json_output_config(
            {
                "type": "object",
                "properties": {
                    "maximum": {"type": "number", "minimum": 0},
                    "properties": {
                        "type": "object",
                        "properties": {"x": {"type": "string"}},
                    },
                },
                "$defs": {"line": {"type": "object", "properties": {}}},
            }
        )["format"]["schema"]
        self.assertEqual(sorted(schema["properties"]), ["maximum", "properties"])
        self.assertNotIn("minimum", schema["properties"]["maximum"])
        nested = schema["properties"]["properties"]
        self.assertEqual(sorted(nested["properties"]), ["x"])
        self.assertIs(nested["additionalProperties"], False)
        self.assertIs(schema["$defs"]["line"]["additionalProperties"], False)
        self.assertNotIn("additionalProperties", schema["$defs"])

    def test_a_callers_output_config_is_kept_beside_the_format(self):
        body = {"content": [{"type": "text", "text": "{}"}], "stop_reason": "end_turn"}
        with patch.object(self.client._client, "post", return_value=_ok(body)) as post:
            self.client.structured_output(
                "x",
                {"type": "object", "properties": {}},
                model="claude-fable-5-1",
                output_config={"effort": "low"},
            )
        sent = post.call_args.kwargs["json"]["output_config"]
        self.assertEqual(sent["effort"], "low")
        self.assertEqual(sent["format"]["type"], "json_schema")

    def test_the_default_output_budget_leaves_room_to_think(self):
        body = {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
        with patch.object(self.client._client, "post", return_value=_ok(body)) as post:
            self.client.simple_completion("hi", model="claude-opus-5")
        self.assertGreaterEqual(post.call_args.kwargs["json"]["max_tokens"], 16000)


@tagged("post_install", "-at_install")
class TestModelRowsAreTheCatalogue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        credential_for(cls.env, "claude", api_key="K")
        credential_for(cls.env, "openai", bearer_token="K")

    _BASE_LOGGER = "odoo.addons.gateway_ml.tools.ai_clients.base"

    def test_a_model_with_a_row_is_known_without_a_class_list(self):
        openai = self.env["gateway.ml.provider"].search([("code", "=", "openai")])
        self.env["gateway.ml.model"].create(
            {"provider_id": openai.id, "name": "GPT-9", "code": "gpt-9"}
        )
        with self.assertNoLogs(self._BASE_LOGGER, "WARNING"):
            OpenAICompatibleClient(self.env, endpoint_code="openai")._check_params(
                model="gpt-9"
            )

    def test_a_model_nobody_describes_still_warns(self):
        with self.assertLogs(self._BASE_LOGGER, "WARNING"):
            OpenAICompatibleClient(self.env, endpoint_code="openai")._check_params(
                model="gpt-nope"
            )

    def test_the_output_cap_is_the_model_rows(self):
        self.env.ref("gateway_ml.ai_model_claude_haiku_4_5").max_output_tokens = 64000
        client = ClaudeClient(self.env)
        with self.assertLogs(self._BASE_LOGGER, "WARNING"):
            client._check_params(model="claude-haiku-4-5", max_tokens=70000)
        with self.assertNoLogs(self._BASE_LOGGER, "WARNING"):
            client._check_params(model="claude-sonnet-5", max_tokens=100000)
