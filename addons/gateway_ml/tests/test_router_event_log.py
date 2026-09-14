from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.gateway_ml.tools import MlRouter
from odoo.addons.gateway_ml.tools.ai_clients import BaseAIClient
from odoo.addons.integration.tools.api_client import OutboundAPIClient
from odoo.addons.integration.tools.exceptions import CommError


class _StubClient(BaseAIClient):
    ENDPOINT_CODE = "stub"

    def simple_completion(self, prompt, model=None, **kwargs):
        return "stub"


@tagged("post_install", "-at_install")
class TestRouterEventLog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.log = cls.env["integration.exchange"]
        cls.router = MlRouter(cls.env)
        cls._stub_clients = {}
        provider_class = type(cls.env["gateway.ml.provider"])

        def get_stub_client(provider, company_id=None):
            return cls._stub_clients[provider.code](provider.env, company_id=company_id)

        cls.startClassPatcher(
            patch.object(provider_class, "_get_ai_client", get_stub_client)
        )

    def _model(self, code):
        endpoint = self.env["integration.service"].create(
            {
                "name": code,
                "code": code,
                "endpoint_url": "https://example.invalid/v1",
                "auth_type": "bearer",
                "category": "ai",
                "rate_limit_enabled": False,
                "cache_enabled": False,
                "retry_enabled": False,
            }
        )
        credential = self.env["credential.credential"].create(
            {"name": f"{code} key", "endpoint_id": endpoint.id, "bearer_token": "K"}
        )
        endpoint.credential_id = credential
        self._stub_clients[code] = type(
            f"Stub{code}", (_StubClient,), {"ENDPOINT_CODE": code}
        )
        provider = self.env["gateway.ml.provider"].create({"endpoint_id": endpoint.id})
        provider.default_model_id = self.env["gateway.ml.model"].create(
            {"provider_id": provider.id, "name": f"{code} stub", "code": f"{code}-m"}
        )
        return provider.default_model_id

    def _rows(self):
        return self.log.sudo().search([], order="id desc")

    def _run(self, request_func, ai_model, **kwargs):
        return self.router.run_with_fallback(
            primary_model=ai_model, request_func=request_func, **kwargs
        )

    def test_a_successful_call_leaves_one_row(self):
        provider = self._model("orch_ok")
        before = len(self._rows())

        def request_func(client, _provider):
            client._client._queue_event_log(
                "POST",
                "https://example.invalid/v1/chat",
                {"json": {"x": 1}},
                {
                    "status_code": 200,
                    "headers": {},
                    "body": {"ok": True},
                    "elapsed_ms": 3,
                },
                "trace-1",
            )
            return "answer"

        self.assertEqual(self._run(request_func, provider), "answer")
        self.env.flush_all()
        self.env.cr.precommit.run()

        rows = self._rows()
        self.assertEqual(
            len(rows) - before,
            1,
            "one exchange must leave one row; the orchestrator this router replaced used to add a "
            "second with an invented status code",
        )

    def test_the_row_carries_the_provider_and_chain_position(self):
        provider = self._model("orch_tag")

        def request_func(client, _provider):
            client._client._queue_event_log(
                "POST",
                "https://example.invalid/v1/chat",
                {"json": {}},
                {"status_code": 200, "headers": {}, "body": {}, "elapsed_ms": 1},
                "trace-2",
            )
            return "ok"

        self._run(
            request_func, provider, log_metadata={"origin_model": "ir.attachment"}
        )
        self.env.flush_all()
        self.env.cr.precommit.run()

        row = self._rows()[0]
        self.assertIn("ai_provider:orch_tag", row.tags)
        self.assertIn("fallback:False", row.tags)
        self.assertEqual(
            row.origin_model,
            "ir.attachment",
            "a caller's log_metadata still reaches the row",
        )
        self.assertEqual(
            row.status_code, 200, "the status is the vendor's, not a constant"
        )

    @mute_logger("odoo.addons.gateway_ml.tools.router")
    def test_a_fallback_names_who_it_followed(self):
        primary = self._model("orch_first")
        backup = self._model("orch_second")

        def request_func(client, ai_model):
            if ai_model == primary:
                raise ValueError("primary is down")
            client._client._queue_event_log(
                "POST",
                "https://example.invalid/v1/chat",
                {"json": {}},
                {"status_code": 200, "headers": {}, "body": {}, "elapsed_ms": 1},
                "trace-3",
            )
            return "recovered"

        result = self._run(request_func, primary, fallback_chain=[backup])
        self.assertEqual(result, "recovered")
        self.env.flush_all()
        self.env.cr.precommit.run()

        row = self._rows()[0]
        self.assertIn("ai_model:orch_second-m", row.tags)
        self.assertIn("fallback:True", row.tags)
        self.assertIn(
            "after:orch_first-m",
            row.tags,
            "the chain must stay reconstructable from the row itself",
        )

    @mute_logger("odoo.addons.gateway_ml.tools.router")
    def test_two_hops_on_one_provider_stay_distinguishable(self):
        primary = self._model("orch_same")
        sibling = self.env["gateway.ml.model"].create(
            {
                "provider_id": primary.provider_id.id,
                "name": "orch_same cheap",
                "code": "orch_same-cheap",
            }
        )

        def request_func(client, ai_model):
            if ai_model == primary:
                raise ValueError("primary is down")
            client._client._queue_event_log(
                "POST",
                "https://example.invalid/v1/chat",
                {"json": {}},
                {"status_code": 200, "headers": {}, "body": {}, "elapsed_ms": 1},
                "trace-5",
            )
            return "recovered"

        self._run(request_func, primary, fallback_chain=[sibling])
        self.env.flush_all()
        self.env.cr.precommit.run()

        row = self._rows()[0]
        self.assertIn("ai_provider:orch_same", row.tags)
        self.assertIn(
            "ai_model:orch_same-cheap",
            row.tags,
            "both hops carry the same provider tag, so only the model tag says "
            "which of them wrote this row",
        )
        self.assertIn("after:orch_same-m", row.tags)

    @mute_logger("odoo.addons.gateway_ml.tools.router")
    def test_a_failure_before_the_request_writes_no_row(self):
        provider = self._model("orch_never")
        before = len(self._rows())

        def request_func(_client, _provider):
            raise ValueError("never reached the wire")

        with self.assertRaises(CommError):
            self._run(request_func, provider)
        self.env.flush_all()
        self.env.cr.precommit.run()

        self.assertEqual(
            len(self._rows()),
            before,
            "an attempt that never sent a request must not fabricate an "
            "integration.exchange row",
        )

    def test_annotations_cannot_overwrite_the_transports_own_facts(self):
        provider = self._model("orch_guard")
        hostile = {
            "tags": "kept",
            "status_code": 999,
            "duration_ms": 1,
            "response_payload": "forged",
        }

        def request_func(client, _provider):
            transport = client._client
            transport.env = transport.env(
                context={
                    **transport.env.context,
                    OutboundAPIClient.EVENT_LOG_ANNOTATIONS_KEY: hostile,
                }
            )
            transport._queue_event_log(
                "POST",
                "https://example.invalid/v1/chat",
                {"json": {}},
                {"status_code": 200, "headers": {}, "body": {}, "elapsed_ms": 7},
                "trace-4",
            )
            return "ok"

        self._run(request_func, provider)
        self.env.flush_all()
        self.env.cr.precommit.run()

        row = self._rows()[0]
        self.assertEqual(row.tags, "kept", "an allowlisted annotation applies")
        self.assertEqual(
            row.status_code, 200, "status_code is the transport's, not the caller's"
        )
        self.assertEqual(row.duration_ms, 7)
        self.assertNotEqual(row.response_payload, "forged")

    def test_the_allowlist_is_what_the_transport_enforces(self):
        self.assertEqual(
            OutboundAPIClient._ANNOTATION_FIELDS,
            ("tags", "origin_model", "origin_record_id"),
        )
