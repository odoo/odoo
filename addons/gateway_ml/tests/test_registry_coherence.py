from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.models.gateway_ml_provider_service import WIRES
from odoo.addons.gateway_ml.tools.ai_clients import WIRE_CLIENTS, get_client_class
from odoo.addons.gateway_ml.tools.wire_formats import UNTIMED_TRANSCRIPTION_MODELS

NO_CHAT_OPERATION = {"deepgram"}


@tagged("post_install", "-at_install")
class TestRegistryCoherence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.providers = cls.env["gateway.ml.provider"].sudo().search([])

    def test_every_provider_has_a_client(self):
        for provider in self.providers:
            with self.subTest(provider=provider.code):
                self.assertTrue(get_client_class(provider))

    def test_every_wire_has_a_client(self):
        self.assertEqual(set(WIRE_CLIENTS), {code for code, _label in WIRES})

    def test_every_provider_carries_a_chat_operation_or_is_exempt(self):
        for provider in self.providers:
            chat = provider.service_ids.filtered(lambda row: row.operation == "chat")
            with self.subTest(provider=provider.code):
                self.assertEqual(
                    bool(chat),
                    provider.code not in NO_CHAT_OPERATION,
                    f"{provider.code} must carry a chat operation unless it is "
                    f"listed in NO_CHAT_OPERATION, and not both",
                )

    def test_every_provider_has_a_default_model_row(self):
        for provider in self.providers:
            with self.subTest(provider=provider.code):
                self.assertTrue(
                    provider.default_model_id,
                    f"{provider.code} names no default model; _resolve_model "
                    f"would fall through to the chat operation for every request",
                )
                self.assertEqual(
                    provider.default_model_id.provider_id,
                    provider,
                    "a provider's default model must be one of its own",
                )

    def test_every_whisper_transcription_row_says_if_it_is_timed(self):
        operations = self.env["gateway.ml.provider.service"].search(
            [
                ("operation", "in", ("transcribe", "transcribe_timed")),
                ("wire", "=", "openai_compatible"),
            ]
        )
        self.assertTrue(operations)
        for operation in operations:
            model = operation.model_id
            with self.subTest(operation=operation.display_name, model=model.code):
                self.assertEqual(
                    model.has_timestamps,
                    model.code not in UNTIMED_TRANSCRIPTION_MODELS,
                    "the wire and the row disagree on whether it times its words",
                )
                if operation.operation == "transcribe_timed":
                    self.assertTrue(model.has_timestamps)

    def test_has_audio_means_the_routers_client_can_transcribe(self):
        for provider in self.providers.filtered("has_audio"):
            client_cls = get_client_class(provider)
            with self.subTest(provider=provider.code):
                self.assertIsNotNone(client_cls)
                entry_points = [
                    name
                    for name in dir(client_cls)
                    if name.startswith("transcribe")
                    and callable(getattr(client_cls, name, None))
                ]
                self.assertTrue(
                    entry_points,
                    f"{provider.code} claims has_audio but {client_cls.__name__} "
                    f"exposes no transcribe* method; the router would "
                    f"select it and the call would fail at the attribute",
                )

    def test_the_capability_roll_ups_derive_from_the_model_rows(self):
        for provider in self.providers:
            with self.subTest(provider=provider.code):
                self.assertEqual(
                    provider.has_vision,
                    any(provider.model_ids.mapped("has_vision")),
                )
                self.assertEqual(
                    provider.has_audio,
                    "audio" in provider.model_ids.mapped("kind"),
                )

    def test_no_model_falls_back_to_itself(self):
        for model in self.env["gateway.ml.model"].sudo().search([]):
            with self.subTest(model=model.code):
                self.assertNotIn(
                    model,
                    model.fallback_model_ids,
                    "a model listing itself as its own fallback retries the "
                    "request that just failed, against the same wire",
                )

    def test_a_fallback_hop_is_reachable(self):
        for model in self.env["gateway.ml.model"].sudo().search([]):
            for hop in model.fallback_model_ids:
                with self.subTest(model=model.code, hop=hop.code):
                    self.assertTrue(
                        get_client_class(hop.provider_id),
                        f"{model.code} falls back to {hop.code} on "
                        f"{hop.provider_id.code}, which has no client class; the "
                        f"hop would fail at _get_ai_client rather than on the wire",
                    )

    def test_every_model_belongs_to_the_provider_it_is_listed_under(self):
        for model in self.env["gateway.ml.model"].sudo().search([]):
            with self.subTest(model=model.code):
                self.assertIn(
                    model,
                    model.provider_id.model_ids,
                    "a model reachable through no provider cannot be run",
                )
