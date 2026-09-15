from unittest.mock import MagicMock, patch

import requests

from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged

from odoo.addons.integration.tools.connection_gate import ConnectionUnavailable

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
