from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tools.ai_clients import AI_CLIENT_REGISTRY
from odoo.addons.gateway_ml.tools.vendor_catalog import (
    PROVIDERS,
    UNTIMED_TRANSCRIPTION_MODELS,
)

CATALOG_EXEMPT = {"deepgram"}

NOT_A_PROVIDER = {"gemini_openai"}


@tagged("post_install", "-at_install")
class TestRegistryCoherence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.providers = cls.env["gateway.ml.provider"].sudo().search([])
        cls.provider_codes = set(cls.providers.mapped("code"))

    def test_every_catalog_key_is_an_endpoint_code(self):
        endpoints = set(
            self.env["integration.service"].sudo().search([]).mapped("code")
        )
        for key in PROVIDERS:
            with self.subTest(vendor=key):
                self.assertIn(
                    key,
                    endpoints,
                    f"catalog key {key!r} names no integration.service; a "
                    f"vendor must have one name across all four registries",
                )

    def test_every_catalog_vendor_is_selectable(self):
        for key in PROVIDERS:
            with self.subTest(vendor=key):
                self.assertIn(key, self.provider_codes, f"{key} has no gateway.ml.provider row")
                self.assertIn(
                    key,
                    AI_CLIENT_REGISTRY,
                    f"{key} has no client class, so _get_ai_client would raise "
                    f"for any provider the orchestrator selected",
                )

    def test_every_provider_has_a_client(self):
        for code in sorted(self.provider_codes):
            with self.subTest(provider=code):
                self.assertIn(code, AI_CLIENT_REGISTRY)

    def test_every_provider_is_in_the_catalog_or_exempt(self):
        for code in sorted(self.provider_codes - CATALOG_EXEMPT):
            with self.subTest(provider=code):
                self.assertIn(
                    code,
                    PROVIDERS,
                    f"{code} is selectable but the catalog does not describe it, "
                    f"so its model and timeouts have no single source. Add an "
                    f"entry, or list it in CATALOG_EXEMPT with the reason.",
                )

    def test_the_exemptions_are_still_needed(self):
        self.assertFalse(
            CATALOG_EXEMPT & set(PROVIDERS),
            "a vendor listed as catalog-exempt now HAS a catalog entry; drop it "
            "from CATALOG_EXEMPT",
        )
        endpoints = set(
            self.env["integration.service"].sudo().search([]).mapped("code")
        )
        self.assertTrue(
            endpoints >= NOT_A_PROVIDER,
            "NOT_A_PROVIDER names an endpoint that no longer exists",
        )

    def test_every_provider_has_a_default_model_row(self):
        for provider in self.providers:
            with self.subTest(provider=provider.code):
                self.assertTrue(
                    provider.default_model_id,
                    f"{provider.code} names no default model; _resolve_model "
                    f"would fall through to the catalog for every request",
                )
                self.assertEqual(
                    provider.default_model_id.provider_id,
                    provider,
                    "a provider's default model must be one of its own",
                )

    def test_the_default_model_matches_the_catalog(self):
        for provider in self.providers:
            spec = PROVIDERS.get(provider.code)
            if not spec or not spec.get("chat_model"):
                continue
            with self.subTest(provider=provider.code):
                self.assertEqual(
                    provider.default_model_id.code,
                    spec["chat_model"],
                    "seed and catalog disagree about the default model — the "
                    "exact drift _resolve_model was written to stop",
                )

    def test_vision_matches_the_catalog(self):
        for provider in self.providers:
            spec = PROVIDERS.get(provider.code)
            if not spec:
                continue
            with self.subTest(provider=provider.code):
                self.assertEqual(
                    provider.has_vision,
                    bool(spec.get("vision")),
                    "the vendor-level roll-up and the catalog's vision key "
                    "describe the same capability and must not disagree",
                )

    def test_a_distinct_vision_model_has_a_row_and_a_blind_chat_model(self):
        for provider in self.providers:
            spec = PROVIDERS.get(provider.code) or {}
            vision_model = spec.get("vision_model")
            if not vision_model:
                continue
            with self.subTest(provider=provider.code):
                self.assertIn(
                    vision_model,
                    provider.model_ids.mapped("code"),
                    f"{provider.code} sends images to {vision_model!r} and no "
                    f"gateway.ml.model row describes it",
                )
                for model in provider.model_ids.filtered(lambda m: m.kind == "chat"):
                    self.assertFalse(
                        model.has_vision,
                        f"{provider.code} names a separate vision model, so its "
                        f"chat model {model.code!r} is the one that cannot see; "
                        f"claiming otherwise is the bit the provider row used to "
                        f"get wrong",
                    )

    def test_every_catalog_transcription_model_has_a_row_that_says_if_it_is_timed(
        self,
    ):
        for provider in self.providers:
            spec = PROVIDERS.get(provider.code) or {}
            rows = {model.code: model for model in provider.model_ids}
            for key in ("audio_model", "cues_model"):
                code = spec.get(key)
                if not code or spec.get("audio") != "whisper":
                    continue
                with self.subTest(provider=provider.code, key=key):
                    self.assertIn(code, rows, f"no gateway.ml.model row describes {code!r}")
                    self.assertEqual(
                        rows[code].has_timestamps,
                        code not in UNTIMED_TRANSCRIPTION_MODELS,
                        "the wire and the row disagree on whether it times its words",
                    )
            if spec.get("cues_model"):
                with self.subTest(provider=provider.code, key="cues_model timed"):
                    self.assertNotIn(spec["cues_model"], UNTIMED_TRANSCRIPTION_MODELS)

    def test_has_audio_means_the_orchestrators_client_can_transcribe(self):
        for provider in self.providers.filtered("has_audio"):
            client_cls = AI_CLIENT_REGISTRY.get(provider.code)
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
                    f"exposes no transcribe* method; the orchestrator would "
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
                    self.assertIn(
                        hop.provider_id.code,
                        AI_CLIENT_REGISTRY,
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
