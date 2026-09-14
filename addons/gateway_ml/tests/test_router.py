from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.gateway_ml.tools.router import MlRouter, is_retryable
from odoo.addons.integration.tools.exceptions import (
    AuthenticationError,
    ClientError,
    CommError,
    CommTimeoutError,
    RateLimitError,
    ServerError,
    ValidationError,
)


class _FakeClient:
    pass


@tagged("post_install", "-at_install")
class TestRetryClassification(TransactionCase):
    def test_permanent_failures_are_not_retryable(self):
        for exc in (
            AuthenticationError("401"),
            ClientError("400 bad request"),
            ValidationError("schema mismatch"),
        ):
            self.assertFalse(is_retryable(exc), f"{type(exc).__name__} must not retry")

    def test_transient_failures_are_retryable(self):
        for exc in (
            ServerError("503"),
            CommTimeoutError("timed out"),
            RateLimitError("429"),
            CommError("something generic"),
        ):
            self.assertTrue(is_retryable(exc), f"{type(exc).__name__} must retry")

    def test_unknown_exceptions_stay_retryable(self):
        self.assertTrue(is_retryable(RuntimeError("who knows")))


@tagged("post_install", "-at_install")
class TestExecuteWithFallback(TransactionCase):
    def setUp(self):
        super().setUp()
        self.models = self.env["gateway.ml.model"].search(
            [("kind", "=", "chat")], limit=4
        )
        if len(self.models) < 3:
            self.skipTest("need at least 3 seeded chat models")
        self.primary = self.models[0]
        self.rest = self.models[1:]
        self.primary.fallback_model_ids = [(6, 0, self.rest.ids)]
        self.router = MlRouter(self.env)
        patcher = patch.object(
            MlRouter,
            "_get_usable_providers",
            side_effect=lambda providers, company_id=None: providers,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _run(self, raiser, use_assert_raises=True):
        attempted = []

        def recording(client, ai_model):
            attempted.append(ai_model.code)
            return raiser(client, ai_model)

        with patch.object(
            MlRouter,
            "_get_client",
            side_effect=lambda p, company_id=None: _FakeClient(),
        ):
            if use_assert_raises:
                with self.assertRaises(CommError):
                    self.router.run_with_fallback(self.primary, recording)
            else:
                raised = None
                try:
                    self.router.run_with_fallback(self.primary, recording)
                except CommError as exc:
                    raised = exc
                self.assertIsNotNone(raised, "the chain should have raised CommError")
        return attempted

    def test_auth_error_stops_at_the_first_provider(self):
        attempted = self._run(
            lambda client, provider: (_ for _ in ()).throw(
                AuthenticationError("401 Unauthorized: invalid x-api-key")
            )
        )
        self.assertEqual(
            attempted,
            [self.primary.code],
            "a bad credential for one provider must not be asked of the others",
        )

    def test_client_error_stops_at_the_first_provider(self):
        attempted = self._run(
            lambda client, provider: (_ for _ in ()).throw(ClientError("400"))
        )
        self.assertEqual(attempted, [self.primary.code])

    def test_server_error_walks_the_whole_chain(self):
        attempted = self._run(
            lambda client, provider: (_ for _ in ()).throw(ServerError("503"))
        )
        self.assertEqual(len(attempted), len(self.models))

    def test_rate_limit_walks_the_chain(self):
        attempted = self._run(
            lambda client, provider: (_ for _ in ()).throw(RateLimitError("429"))
        )
        self.assertEqual(len(attempted), len(self.models))

    def test_a_non_retryable_failure_fabricates_no_exchange(self):
        model = self.env["integration.exchange"]
        before = model.search([("direction", "=", "outbound")]).ids
        attempted = self._run(
            lambda client, provider: (_ for _ in ()).throw(AuthenticationError("401")),
            use_assert_raises=False,
        )
        self.env.flush_all()
        self.env.cr.precommit.run()

        self.assertEqual(attempted, [self.primary.code], "the chain must stop")
        written = model.search([("direction", "=", "outbound")]).filtered(
            lambda log: log.id not in before
        )
        self.assertFalse(
            written,
            f"nothing reached the wire, so nothing may claim an exchange; got "
            f"{written.mapped('tags')}",
        )

    def test_a_retryable_failure_walks_the_chain_without_inventing_rows(self):
        model = self.env["integration.exchange"]
        before = model.search([("direction", "=", "outbound")]).ids
        attempted = self._run(
            lambda client, provider: (_ for _ in ()).throw(ServerError("503")),
            use_assert_raises=False,
        )
        self.env.flush_all()
        self.env.cr.precommit.run()

        self.assertEqual(len(attempted), len(self.models), "every hop is tried")
        written = model.search([("direction", "=", "outbound")]).filtered(
            lambda log: log.id not in before
        )
        self.assertFalse(written, "a fake client exchanges nothing")

    def test_success_on_a_fallback_returns_its_result(self):
        def fail_then_succeed(client, ai_model):
            if ai_model == self.primary:
                raise ServerError("503")
            return {"ok": ai_model.code}

        seen = self._run_ok(fail_then_succeed)
        self.assertEqual(seen, [self.primary.code, self.rest[0].code])
        self.assertEqual(self.result, {"ok": self.rest[0].code})

    def test_success_on_the_primary_asks_nobody_else(self):
        seen = self._run_ok(lambda client, ai_model: "done")
        self.assertEqual(seen, [self.primary.code])
        self.assertEqual(self.result, "done")

    def test_a_hop_may_stay_on_the_same_provider(self):
        sibling = self.env["gateway.ml.model"].create(
            {
                "provider_id": self.primary.provider_id.id,
                "name": f"{self.primary.name} (cheap)",
                "code": f"{self.primary.code}-cheap",
            }
        )
        self.primary.fallback_model_ids = [(6, 0, sibling.ids)]

        def fail_then_succeed(client, ai_model):
            if ai_model == self.primary:
                raise ServerError("503")
            return "recovered"

        seen = self._run_ok(fail_then_succeed)
        self.assertEqual(seen, [self.primary.code, sibling.code])
        self.assertEqual(
            sibling.provider_id,
            self.primary.provider_id,
            "the fallback ran on the key the primary already used",
        )

    def _run_ok(self, request_func):
        seen = []

        def recording(client, ai_model):
            seen.append(ai_model.code)
            return request_func(client, ai_model)

        with patch.object(
            MlRouter,
            "_get_client",
            side_effect=lambda p, company_id=None: _FakeClient(),
        ):
            self.result = self.router.run_with_fallback(self.primary, recording)
        return seen


@tagged("post_install", "-at_install")
class TestOptimizeModelSelection(TransactionCase):
    def setUp(self):
        super().setUp()
        self.router = MlRouter(self.env)
        one_per_provider = self.env["gateway.ml.model"]
        seen_providers = self.env["gateway.ml.provider"]
        for model in self.env["gateway.ml.model"].search([("kind", "=", "chat")]):
            if model.provider_id in seen_providers:
                continue
            seen_providers |= model.provider_id
            one_per_provider |= model
        self.models = one_per_provider[:3]
        if len(self.models) < 3:
            self.skipTest("need at least 3 seeded models on distinct providers")
        self.cheap, self.accurate, self.fast = (
            self.models[0],
            self.models[1],
            self.models[2],
        )
        self.models.provider_id.write({"has_free_tier": False})
        self.models.write({"cost_per_1m_output": 0.0})
        self.cheap.write(
            {"cost_per_1m_input": 0.10, "accuracy_rating": "2", "speed_rating": "2"}
        )
        self.accurate.write(
            {"cost_per_1m_input": 30.0, "accuracy_rating": "5", "speed_rating": "2"}
        )
        self.fast.write(
            {"cost_per_1m_input": 5.0, "accuracy_rating": "3", "speed_rating": "5"}
        )

    def test_cost_picks_the_cheapest(self):
        self.assertEqual(self.router._rank(self.models, "cost")[0], self.cheap)

    def test_a_free_tier_does_not_outrank_a_cheaper_model(self):
        self.accurate.provider_id.has_free_tier = True
        self.assertEqual(self.router._rank(self.models, "cost")[0], self.cheap)

    def test_a_free_tier_breaks_a_tie_on_price(self):
        self.accurate.write({"cost_per_1m_input": 0.10})
        self.accurate.provider_id.has_free_tier = True
        self.assertEqual(self.router._rank(self.models, "cost")[0], self.accurate)

    def test_accuracy_picks_the_highest_rated(self):
        self.assertEqual(
            self.router._rank(self.models, "accuracy")[0],
            self.accurate,
        )

    def test_speed_picks_the_fastest(self):
        self.assertEqual(self.router._rank(self.models, "speed")[0], self.fast)

    def test_balanced_ranks_every_candidate(self):
        self.assertEqual(
            set(self.router._rank(self.models, "balanced").ids), set(self.models.ids)
        )

    def test_an_unknown_strategy_is_refused(self):
        with self.assertRaises(ValueError):
            self.router.select_model("chat", optimize_for="no-such-strategy")

    def test_empty_recordset_ranks_empty(self):
        self.assertFalse(
            self.router._rank(self.env["gateway.ml.model"].browse(), "cost")
        )
