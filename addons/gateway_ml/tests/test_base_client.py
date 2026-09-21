import inspect
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.gateway_ml.tools.ai_clients import (
    WIRE_CLIENTS,
    BaseAIClient,
    ClaudeClient,
    GeminiClient,
    OpenAICompatibleClient,
    get_client_class,
)

CLIENTS = tuple(WIRE_CLIENTS.values())


class _Probe(BaseAIClient):
    ENDPOINT_CODE = "probe"
    FALLBACK_MODEL = "probe-fallback"
    VALID_MODELS = ("probe-1", "probe-2")
    MIN_TEMPERATURE = 0.0
    MAX_TEMPERATURE = 1.0
    MAX_TOKENS_LIMIT = 100

    def __init__(self, env):
        self.env = env
        self.company_id = None


@tagged("post_install", "-at_install")
class TestClientContract(TransactionCase):
    def test_all_clients_subclass_the_base(self):
        for cls in CLIENTS:
            self.assertTrue(issubclass(cls, BaseAIClient), cls.__name__)

    def test_a_client_bound_to_no_service_refuses_to_build(self):
        with self.assertRaises(NotImplementedError):
            OpenAICompatibleClient(self.env)

    def test_every_client_resolves_a_model_with_nothing_to_go_on(self):
        for provider in self.env["gateway.ml.provider"].search([]):
            cls = get_client_class(provider)
            with self.subTest(provider=provider.code, client=cls.__name__):
                client = cls.__new__(cls)
                client.env = self.env
                client.ENDPOINT_CODE = provider.code
                client._default_model = ""
                self.assertTrue(
                    client._resolve_model(),
                    f"{cls.__name__} resolves no model without a gateway.ml.provider "
                    f"row: its ENDPOINT_CODE has no chat operation row and it "
                    f"carries no FALLBACK_MODEL.",
                )

    def test_no_client_redefines_validate_params(self):
        for cls in CLIENTS:
            self.assertNotIn(
                "_check_params",
                cls.__dict__,
                f"{cls.__name__} shadows the shared _check_params",
            )

    def test_every_client_validates(self):
        for cls in CLIENTS:
            self.assertTrue(hasattr(cls, "_check_params"), cls.__name__)


@tagged("post_install", "-at_install")
class TestModelResolution(TransactionCase):
    def test_explicit_model_wins(self):
        probe = _Probe(self.env)
        with patch.object(
            _Probe, "_provider_default_model", return_value="from-record"
        ):
            self.assertEqual(probe._resolve_model("explicit"), "explicit")

    def test_provider_record_beats_the_class_constant(self):
        probe = _Probe(self.env)
        with patch.object(
            _Probe, "_provider_default_model", return_value="from-record"
        ):
            self.assertEqual(probe._resolve_model(None), "from-record")

    def test_fallback_used_when_the_record_is_unset(self):
        probe = _Probe(self.env)
        with patch.object(_Probe, "_provider_default_model", return_value=""):
            self.assertEqual(probe._resolve_model(None), "probe-fallback")

    def test_configured_default_model_is_honoured(self):
        provider = self.env["gateway.ml.provider"].search(
            [("code", "=", "claude")], limit=1
        )
        if not provider:
            self.skipTest("claude provider seed missing")
        code = "claude-opus-5"
        model = self.env["gateway.ml.model"].search(
            [("provider_id", "=", provider.id), ("code", "=", code)], limit=1
        ) or self.env["gateway.ml.model"].create(
            {"provider_id": provider.id, "name": "Claude Opus 5", "code": code}
        )
        provider.default_model_id = model

        client = ClaudeClient.__new__(ClaudeClient)
        client.env = self.env
        client.company_id = None
        self.assertEqual(client._resolve_model(None), code)

    def test_resolution_survives_a_missing_provider_row(self):
        client = OpenAICompatibleClient.__new__(OpenAICompatibleClient)
        client.env = self.env
        client.company_id = None
        client.ENDPOINT_CODE = "openai"
        with patch.object(
            OpenAICompatibleClient, "_provider_default_model", return_value=""
        ):
            self.assertEqual(client._resolve_model(None), "gpt-5.6-luna")


@tagged("post_install", "-at_install")
class TestValidateParams(TransactionCase):
    def setUp(self):
        super().setUp()
        self.probe = _Probe(self.env)

    def test_valid_temperature_accepted(self):
        self.probe._check_params(temperature=0.5)

    def test_temperature_bounds(self):
        for bad in (-0.1, 1.5):
            with self.assertRaises(ValueError):
                self.probe._check_params(temperature=bad)

    def test_temperature_must_be_numeric(self):
        with self.assertRaises(ValueError):
            self.probe._check_params(temperature="warm")

    def test_bool_is_not_a_temperature(self):
        with self.assertRaises(ValueError):
            self.probe._check_params(temperature=True)

    def test_max_tokens_must_be_a_positive_int(self):
        for bad in (0, -5, 1.5, "many"):
            with self.assertRaises(ValueError):
                self.probe._check_params(max_tokens=bad)

    def test_bool_is_not_a_token_count(self):
        with self.assertRaises(ValueError):
            self.probe._check_params(max_tokens=True)

    def test_max_tokens_over_the_limit_only_warns(self):
        self.probe._check_params(max_tokens=self.probe.MAX_TOKENS_LIMIT + 1)

    def test_unknown_model_only_warns(self):
        self.probe._check_params(model="probe-99")

    def test_known_model_accepted(self):
        self.probe._check_params(model="probe-1")

    def test_empty_allowlist_accepts_anything(self):
        class Open(_Probe):
            VALID_MODELS = ()

        Open(self.env)._check_params(model="whatever")


@tagged("post_install", "-at_install")
class TestCompleteContract(TransactionCase):
    CHAT_CLIENTS = (ClaudeClient, GeminiClient, OpenAICompatibleClient)
    REMOVED = (
        "simple_completion",
        "vision_completion",
        "json_completion",
        "multimodal_completion",
        "streaming_completion",
        "get_usage",
    )

    def test_every_chat_client_takes_the_declared_signature(self):
        declared = inspect.signature(BaseAIClient.complete)
        for cls in self.CHAT_CLIENTS:
            with self.subTest(client=cls.__name__):
                self.assertIsNot(cls.complete, BaseAIClient.complete)
                self.assertEqual(inspect.signature(cls.complete), declared)

    def test_no_client_keeps_a_chat_method_complete_replaced(self):
        for cls in CLIENTS:
            for name in self.REMOVED:
                with self.subTest(client=cls.__name__, method=name):
                    self.assertFalse(hasattr(cls, name))

    def test_complete_is_the_declared_primitive(self):
        class Textless(BaseAIClient):
            ENDPOINT_CODE = "textless"

        client = Textless.__new__(Textless)
        client.env = self.env
        with self.assertRaises(NotImplementedError):
            client.complete("hi")
