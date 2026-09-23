from unittest.mock import MagicMock, patch

import requests

from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged

from odoo.addons.integration.tools.connection_gate import (
    BudgetSpent,
    ConnectionUnavailable,
)

URL = "https://api.example.com/v1/charge"


@tagged("post_install", "-at_install", "integration")
class TestConnectionGate(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Gate Probe"})
        self.connection = self.env["integration.connection"]._for_record(
            self.partner, "probe_gate", "Probe gate", "other"
        )
        self.connection.write(
            {
                "breaker_failure_threshold": 2,
                "breaker_failure_window": 60,
                "breaker_max_cooldown": 60,
            }
        )

    def _call(self, **patched):
        with patch.object(GuardedSession, "request", **patched) as sent:
            try:
                return self.connection._egress_request(
                    "POST", URL, purpose="probe_gate"
                ), sent
            except requests.RequestException as error:
                return error, sent

    def test_a_keyword_call_reaches_the_session_as_keywords(self):
        with patch.object(
            GuardedSession, "request", return_value=MagicMock(status_code=200)
        ) as sent:
            session = self.connection._egress_session("probe_gate")
            session.request(method="POST", url=URL, json={})

        self.assertEqual(
            sent.call_args.kwargs, {"method": "POST", "url": URL, "json": {}}
        )

    def test_a_record_gets_one_connection_on_a_per_record_service(self):
        again = self.env["integration.connection"]._for_record(
            self.partner, "probe_gate", "Probe gate", "other"
        )

        self.assertEqual(again, self.connection)
        self.assertEqual(
            (self.connection.res_model, self.connection.res_id),
            ("res.partner", self.partner.id),
        )
        self.assertTrue(self.connection.service_id.per_record_connections)
        self.assertEqual(self.connection.service_id.code, "probe_gate")

    def test_a_call_is_recorded_against_its_connection(self):
        self._call(return_value=MagicMock(status_code=200))
        self.env.flush_all()
        self.env.cr.precommit.run()

        row = self.env["integration.exchange"].search(
            [("tags", "=", "egress:probe_gate")], order="id desc", limit=1
        )
        self.assertEqual(row.connection_id, self.connection)

    def test_a_call_whose_connection_was_rolled_back_is_still_recorded(self):
        partner = self.env["res.partner"].create({"name": "Rolled Back Probe"})
        with self.assertRaises(requests.ConnectionError):
            with self.env.cr.savepoint():
                connection = self.env["integration.connection"]._for_record(
                    partner, "probe_gate", "Probe gate", "other"
                )
                with patch.object(
                    GuardedSession,
                    "request",
                    side_effect=requests.ConnectionError("down"),
                ):
                    connection._egress_request("POST", URL, purpose="probe_rollback")

        self.env.flush_all()
        self.env.cr.precommit.run()

        row = self.env["integration.exchange"].search(
            [("tags", "=", "egress:probe_rollback")], order="id desc", limit=1
        )
        self.assertTrue(row)
        self.assertFalse(row.connection_id)

    def test_repeated_failures_pause_the_connection_and_calls_stop_leaving(self):
        for _ in range(2):
            error, _sent = self._call(side_effect=requests.ConnectTimeout("down"))
            self.assertIsInstance(error, requests.Timeout)

        error, sent = self._call(return_value=MagicMock(status_code=200))

        self.assertIsInstance(error, ConnectionUnavailable)
        self.assertIsInstance(error, requests.ConnectionError)
        sent.assert_not_called()
        self.env.flush_all()
        self.env.cr.precommit.run()
        self.assertEqual(self.connection.circuit_state, "open")
        self.assertIn("down", self.connection.last_error)

    def test_a_server_error_counts_and_a_client_error_does_not(self):
        for _ in range(3):
            self._call(return_value=MagicMock(status_code=422))
        response, sent = self._call(return_value=MagicMock(status_code=200))
        self.assertEqual(response.status_code, 200)

        for _ in range(2):
            self._call(return_value=MagicMock(status_code=503))
        error, sent = self._call(return_value=MagicMock(status_code=200))
        self.assertIsInstance(error, ConnectionUnavailable)
        sent.assert_not_called()

    def test_a_successful_probe_closes_the_connection_again(self):
        for _ in range(2):
            self._call(side_effect=requests.ConnectionError("down"))
        breaker = self.env.registry._integration_connection_breakers.get(
            self.connection.id, 2, 60, 60
        )
        with patch("odoo.libs.breaker.monotonic", return_value=10**9):
            response, _sent = self._call(return_value=MagicMock(status_code=200))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(breaker.closed)
        self.env.flush_all()
        self.env.cr.precommit.run()
        self.assertEqual(self.connection.circuit_state, "closed")
        self.assertTrue(self.connection.last_success_at)

    def test_a_late_success_from_before_the_trip_does_not_record_a_close(self):
        breaker = self.env.registry._integration_connection_breakers.get(
            self.connection.id, 2, 60, 60
        )
        before_the_trip = breaker.acquire_attempt()
        for _ in range(2):
            self._call(side_effect=requests.ConnectionError("down"))
        self.assertFalse(breaker.closed)

        self.connection._settle_call(
            response=MagicMock(status_code=200), attempt=before_the_trip
        )

        self.assertFalse(breaker.closed)
        self.env.flush_all()
        self.env.cr.precommit.run()
        self.assertEqual(self.connection.circuit_state, "open")

    def test_an_attempt_of_a_replaced_breaker_does_not_settle_the_new_one(self):
        from odoo.addons.integration.tools.connection_gate import breaker_for

        def probing(breaker):
            breaker.record_failure(breaker.acquire_attempt())
            breaker.record_failure(breaker.acquire_attempt())
            breaker._opened_at -= breaker._cooldown + 1
            return breaker.acquire_attempt()

        old_probe = probing(breaker_for(self.env, self.connection))
        self.connection.breaker_max_cooldown = 120
        new = breaker_for(self.env, self.connection)
        new_probe = probing(new)
        self.assertEqual(old_probe.generation, new_probe.generation)

        self.connection._settle_call(
            response=MagicMock(status_code=200), attempt=old_probe
        )

        self.assertFalse(new.closed, "the old breaker's probe closed the new one")

    def test_a_probe_refused_by_the_budget_does_not_hold_the_probe_slot(self):
        breaker = self.env.registry._integration_connection_breakers.get(
            self.connection.id, 2, 60, 60
        )
        for _ in range(2):
            self._call(side_effect=requests.ConnectionError("down"))
        self.connection.write({"budget_requests": 1, "budget_window_seconds": 3600})
        self.env["rate.limit.bucket"].consume_for_key(
            f"integration.connection:{self.connection.id}",
            subject_model=self.connection._name,
            subject_id=self.connection.id,
            capacity=1.0,
            window_seconds=3600,
            company_id=self.connection.company_id.id or None,
        )
        with patch("odoo.libs.breaker.monotonic", return_value=10**9):
            with self.assertRaises(BudgetSpent):
                self.connection._admit_call()
            self.assertTrue(breaker.acquire_attempt().probe)

    def test_a_spent_budget_refuses_before_sending(self):
        self.connection.write({"budget_requests": 1, "budget_window_seconds": 3600})
        response, _sent = self._call(return_value=MagicMock(status_code=200))
        self.assertEqual(response.status_code, 200)

        error, sent = self._call(return_value=MagicMock(status_code=200))

        self.assertIsInstance(error, ConnectionUnavailable)
        sent.assert_not_called()

    def test_the_zeep_transport_sends_through_the_connection(self):
        transport = self.connection._zeep_transport("probe_gate", timeout=12)

        self.assertEqual(transport.operation_timeout, 12)
        with patch.object(
            GuardedSession, "request", return_value=MagicMock(status_code=200)
        ):
            transport = self.connection._zeep_transport("probe_gate")
            transport.session.request("POST", URL)
        self.env.flush_all()
        self.env.cr.precommit.run()
        row = self.env["integration.exchange"].search(
            [("tags", "=", "egress:probe_gate")], order="id desc", limit=1
        )
        self.assertEqual(row.connection_id, self.connection)


@tagged("post_install", "-at_install", "integration")
class TestClientPassesTheConnectionGate(TransactionCase):
    """`get_api_client` used to open its own egress session and never touch the
    connection it had resolved, so a service's client ran without the breaker,
    the budget and the response cap that `_egress_request` callers had."""

    def setUp(self):
        super().setUp()
        self.service = self.env["integration.service"].create(
            {
                "name": "Gate Probe Service",
                "code": "gate_probe",
                "category": "other",
                "endpoint_url": "https://api.example.com",
                "allowed_hosts": "api.example.com",
                "environment": "production",
                "auth_type": "none",
                "rate_limit_enabled": False,
                "retry_enabled": False,
            }
        )

    def _client(self):
        from odoo.addons.integration.tools.api_client import get_api_client

        return get_api_client(self.env, "gate_probe")

    def _ok(self):
        response = MagicMock(status_code=200)
        response.headers = {"Content-Type": "application/json"}
        response.json.return_value = {}
        response.text = "{}"
        response.content = b"{}"
        return response

    def test_a_credential_less_service_gets_one_shared_connection(self):
        client = self._client()

        self.assertTrue(client.connection)
        self.assertEqual(client.connection.service_id, self.service)
        self.assertEqual(client.connection.company_id, self.env.company)
        self.assertFalse(client.connection.credential_id)
        self.assertEqual(self._client().connection, client.connection)

    def test_a_spent_connection_budget_refuses_the_client_call(self):
        from odoo.addons.integration.tools.exceptions import RateLimitError

        client = self._client()
        client.connection.write({"budget_requests": 1, "budget_window_seconds": 3600})

        with patch.object(GuardedSession, "request", return_value=self._ok()) as sent:
            client.request("GET", "/one", raw=True)
            with self.assertRaises(RateLimitError):
                client.request("GET", "/two", raw=True)

        self.assertEqual(sent.call_count, 1)

    def test_the_vendor_rate_limit_is_enforced_on_the_same_gate(self):
        from odoo.addons.integration.tools.exceptions import RateLimitError

        self.service.write({"rate_limit_enabled": True, "rate_limit_requests": 1})
        client = self._client()
        bucket = (
            self.env["rate.limit.bucket"]
            .sudo()
            .get_or_create_bucket(self.service, self.env.company.id)
        )
        bucket.write({"tokens": 0.0})

        with patch.object(GuardedSession, "request", return_value=self._ok()) as sent:
            with self.assertRaises(RateLimitError):
                client.request("GET", "/one", raw=True)

        sent.assert_not_called()

    def test_an_open_breaker_refuses_the_client_call_without_sending(self):
        from odoo.addons.integration.tools.exceptions import (
            CircuitOpenError,
            CommError,
        )

        client = self._client()
        client.connection.write(
            {
                "breaker_failure_threshold": 1,
                "breaker_failure_window": 60,
                "breaker_max_cooldown": 60,
            }
        )
        with patch.object(
            GuardedSession,
            "request",
            side_effect=requests.ConnectionError("refused"),
        ):
            with self.assertRaises(CommError):
                client.request("GET", "/one", raw=True)

        with patch.object(GuardedSession, "request", return_value=self._ok()) as sent:
            with self.assertRaises(CircuitOpenError):
                client.request("GET", "/two", raw=True)

        sent.assert_not_called()
        self.env.cr.precommit.run()
        self.assertEqual(client.connection.circuit_state, "open")

    def test_the_client_keeps_the_pipeline_response_cap(self):
        from odoo.libs.guarded_http import DEFAULT_MAX_BYTES

        session = self._client()._create_session()
        self.assertEqual(
            {adapter.max_bytes for adapter in session.adapters.values()},
            {DEFAULT_MAX_BYTES},
        )

        self.service.max_response_bytes = 5
        session = self._client()._create_session()
        self.assertEqual(
            {adapter.max_bytes for adapter in session.adapters.values()}, {5}
        )

    def test_the_zeep_transport_admits_the_wsdl_fetch_and_the_post(self):
        from odoo.addons.integration.tools.exceptions import RateLimitError

        client = self._client()
        client.connection.write({"budget_requests": 2, "budget_window_seconds": 3600})
        transport = client.zeep_transport("https://api.example.com/soap")

        with patch.object(GuardedSession, "request", return_value=self._ok()) as sent:
            transport._load_remote_data("https://api.example.com/x.wsdl")
            transport.post("https://api.example.com/soap", b"<e/>", {})
            with self.assertRaises(RateLimitError):
                transport.post("https://api.example.com/soap", b"<e/>", {})

        self.assertEqual(sent.call_count, 2)
