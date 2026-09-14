from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.gateway_ml.tools.router import MlRouter
from odoo.addons.integration.tools.exceptions import (
    AuthenticationError,
    CommError,
    ServerError,
)


class _SelectionCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["gateway.ml.provider"].search([]).action_archive()
        cls.router = MlRouter(cls.env)

    @classmethod
    def _provider(cls, code, keyed=True, auth_type="bearer", **vals):
        endpoint = cls.env["integration.service"].create(
            {
                "name": code,
                "code": code,
                "endpoint_url": "https://example.invalid/v1",
                "auth_type": auth_type,
                "category": "ai",
            }
        )
        if keyed:
            cls.env["credential.credential"].create(
                {"name": f"{code} key", "endpoint_id": endpoint.id, "bearer_token": "K"}
            )
        return cls.env["gateway.ml.provider"].create(
            {"endpoint_id": endpoint.id, **vals}
        )

    @classmethod
    def _model(cls, provider, code, **vals):
        return cls.env["gateway.ml.model"].create(
            {"provider_id": provider.id, "name": code, "code": code, **vals}
        )


@tagged("post_install", "-at_install")
class TestSelectModel(_SelectionCase):
    def test_kind_is_required(self):
        with self.assertRaises(TypeError):
            self.router.select_model(optimize_for="cost")

    def test_several_kinds_may_be_accepted(self):
        provider = self._provider("sel_kinds")
        vision = self._model(provider, "sel-vision", kind="vision", has_vision=True)
        self._model(provider, "sel-audio2", kind="audio")
        self.assertEqual(
            self.router.select_model(
                kind=("chat", "vision"), required_capabilities={"has_vision": True}
            ),
            vision,
        )

    def test_an_unpriced_model_does_not_win_balanced_by_being_unpriced(self):
        provider = self._provider("sel_price")
        priced = self._model(
            provider, "sel-priced", cost_per_1m_input=0.5, accuracy_rating="4"
        )
        self._model(provider, "sel-unpriced", accuracy_rating="3")
        self.assertEqual(self.router.select_model(kind="chat"), priced)

    def test_audio_is_ranked_on_its_per_minute_price(self):
        provider = self._provider("sel_audio_cost")
        self._model(provider, "sel-a-dear", kind="audio", cost_per_audio_minute=0.02)
        cheap = self._model(
            provider, "sel-z-cheap", kind="audio", cost_per_audio_minute=0.004
        )
        self.assertEqual(
            self.router.select_model(kind="audio", optimize_for="cost"), cheap
        )

    def test_an_unpriced_model_is_not_ranked_behind_an_expensive_one(self):
        provider = self._provider("sel_unpriced_cost")
        self._model(provider, "sel-a-cheap", cost_per_1m_input=0.2)
        self._model(provider, "sel-b-dear", cost_per_1m_input=20.0)
        unpriced = self._model(provider, "sel-c-unpriced")
        ranked = self.router._rank(
            self.env["gateway.ml.model"].search([("provider_id", "=", provider.id)]),
            "cost",
        )
        self.assertLess(
            list(ranked).index(unpriced),
            list(ranked).index(ranked.filtered(lambda m: m.code == "sel-b-dear")),
        )

    def test_the_output_price_counts_toward_cost(self):
        provider = self._provider("sel_blend")
        self._model(
            provider, "sel-a-cheap-in", cost_per_1m_input=1.0, cost_per_1m_output=20.0
        )
        balanced = self._model(
            provider, "sel-z-even", cost_per_1m_input=2.0, cost_per_1m_output=2.0
        )
        self.assertEqual(
            self.router.select_model("chat", optimize_for="cost"), balanced
        )

    def test_an_expired_credential_makes_a_provider_unusable(self):
        provider = self._provider("sel_expired")
        self._model(provider, "sel-expired-m")
        self.env["credential.credential"].search(
            [("endpoint_id", "=", provider.endpoint_id.id)]
        ).date_expiration = fields.Datetime.now() - timedelta(days=1)
        self.assertFalse(self.router.select_model(kind="chat"))

    def test_an_archived_provider_is_not_selected_even_with_a_key(self):
        provider = self._provider("sel_archived")
        self._model(provider, "sel-archived-m")
        provider.endpoint_id.active = False
        self.assertFalse(self.router.select_model("chat"))

    def test_an_endpoint_that_needs_no_key_is_usable_without_one(self):
        keyless = self._model(
            self._provider("sel_none", keyed=False, auth_type="none"), "sel-none-m"
        )
        self.assertEqual(self.router.select_model("chat"), keyless)

    def test_several_providers_may_be_named(self):
        self._model(self._provider("sel_p1"), "sel-p1-m", accuracy_rating="5")
        second = self._model(self._provider("sel_p2"), "sel-p2-m", accuracy_rating="4")
        self._model(self._provider("sel_p3"), "sel-p3-m", accuracy_rating="2")
        self.assertEqual(
            self.router.select_model("chat", provider_code=["sel_p2", "sel_p3"]), second
        )
        self.assertFalse(self.router.select_model("chat", provider_code=[]))

    def test_queries_do_not_grow_with_the_models_a_provider_serves(self):
        provider = self._provider("sel_queries")
        self._model(self._provider("sel_queries_2"), "sel-q2-m")
        self._model(provider, "sel-q-0")

        def count():
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.env.cr.sql_statement_count
            self.router.select_model("chat")
            return self.env.cr.sql_statement_count - before

        few = count()
        for index in range(1, 6):
            self._model(provider, f"sel-q-{index}")
        self.assertEqual(count(), few)

    def test_an_unknown_capability_is_a_programming_error(self):
        self._model(self._provider("sel_unknown"), "sel-unknown-m")
        with self.assertRaises(ValueError):
            self.router.select_model(kind="chat", required_capabilities={"no_such": 1})

    def test_an_unknown_use_case_tag_selects_nothing_rather_than_everything(self):
        self._model(self._provider("sel_tag"), "sel-tag-m")
        self.assertFalse(
            self.router.select_model(kind="chat", use_case_tags=["no-such-tag"])
        )


@tagged("post_install", "-at_install")
class TestFallbackChain(_SelectionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        keyed = cls._provider("fb_keyed")
        cls.primary = cls._model(keyed, "fb-primary")
        cls.sibling = cls._model(keyed, "fb-sibling")
        cls.archived = cls._model(keyed, "fb-archived")
        cls.audio = cls._model(keyed, "fb-audio", kind="audio")
        cls.keyless = cls._model(cls._provider("fb_keyless", keyed=False), "fb-keyless")
        cls.archived.active = False

    def _walk(self, chain, raiser):
        attempted = []

        def request_func(client, ai_model):
            attempted.append(ai_model.code)
            return raiser(ai_model)

        with patch.object(MlRouter, "_get_client", return_value=object()):
            try:
                result = self.router.run_with_fallback(
                    self.primary, request_func, fallback_chain=chain
                )
            except CommError as error:
                result = error
        return attempted, result

    @mute_logger("odoo.addons.gateway_ml.tools.router")
    def test_hops_that_cannot_run_are_not_tried(self):
        def fail(ai_model):
            raise ServerError("503")

        attempted, _result = self._walk(
            [self.primary, self.archived, self.keyless, self.audio, self.sibling],
            fail,
        )
        self.assertEqual(attempted, ["fb-primary", "fb-sibling"])

    @mute_logger("odoo.addons.gateway_ml.tools.router")
    def test_a_vision_model_may_back_up_a_chat_model_that_sees(self):
        seeing_chat = self._model(self._provider("fb_see"), "fb-see", has_vision=True)
        vision = self._model(
            self._provider("fb_vision"), "fb-vision", kind="vision", has_vision=True
        )
        attempted = []

        def fail_first(client, ai_model):
            attempted.append(ai_model.code)
            if ai_model == seeing_chat:
                raise ServerError("503")
            return "seen"

        with patch.object(MlRouter, "_get_client", return_value=object()):
            result = self.router.run_with_fallback(
                seeing_chat, fail_first, fallback_chain=[vision]
            )
        self.assertEqual((attempted, result), (["fb-see", "fb-vision"], "seen"))

    @mute_logger("odoo.addons.gateway_ml.tools.router")
    def test_an_untimed_hop_is_not_tried_for_a_timed_model(self):
        provider = self._provider("fb_timed")
        timed = self._model(provider, "fb-timed", kind="audio", has_timestamps=True)
        untimed = self._model(provider, "fb-untimed", kind="audio")
        also_timed = self._model(
            provider, "fb-also-timed", kind="audio", has_timestamps=True
        )
        attempted = []

        def fail(client, ai_model):
            attempted.append(ai_model.code)
            raise ServerError("503")

        with patch.object(MlRouter, "_get_client", return_value=object()):
            with self.assertRaises(CommError):
                self.router.run_with_fallback(
                    timed, fail, fallback_chain=[untimed, also_timed]
                )
        self.assertEqual(attempted, ["fb-timed", "fb-also-timed"])

    @mute_logger("odoo.addons.gateway_ml.tools.router")
    def test_a_non_retryable_failure_keeps_its_type(self):
        def fail(ai_model):
            raise AuthenticationError("401")

        attempted, result = self._walk([self.sibling], fail)
        self.assertEqual(attempted, ["fb-primary"])
        self.assertIsInstance(result, AuthenticationError)

    def test_caller_metadata_outside_the_allowlist_becomes_a_tag(self):
        annotations = self.router._event_annotations(
            self.primary,
            False,
            None,
            {"feature": "speech.synthesis", "origin_model": "ir.attachment"},
        )
        self.assertIn("feature:speech.synthesis", annotations["tags"].split(","))
        self.assertEqual(annotations["origin_model"], "ir.attachment")


@tagged("post_install", "-at_install")
class TestModelIntegrity(_SelectionCase):
    def test_a_default_model_belongs_to_its_provider(self):
        mine = self._provider("int_mine")
        theirs = self._model(self._provider("int_theirs"), "int-theirs-m")
        with self.assertRaises(ValidationError):
            mine.default_model_id = theirs

    def test_a_vision_model_must_read_images(self):
        with self.assertRaises(ValidationError):
            self._model(self._provider("int_blind"), "int-blind", kind="vision")

    def test_a_timed_model_cannot_fall_back_to_an_untimed_one(self):
        provider = self._provider("int_timed")
        timed = self._model(provider, "int-timed", kind="audio", has_timestamps=True)
        untimed = self._model(provider, "int-untimed", kind="audio")
        with self.assertRaisesRegex(ValidationError, "returns no timestamps"):
            timed.fallback_model_ids = untimed
        untimed.fallback_model_ids = timed

    def test_a_model_cannot_fall_back_to_itself(self):
        model = self._model(self._provider("int_self"), "int-self-m")
        with self.assertRaises(ValidationError):
            model.fallback_model_ids = model
