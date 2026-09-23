import json
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .common import open_admission


@tagged("post_install", "-at_install", "integration")
class TestInboundExchangeRecording(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.receiver = cls.env["integration.receiver"].create(
            {"name": "Probe receiver", "code": "probe_receiver", "auth_type": "none"}
        )

    def _rows(self):
        return (
            self.env["integration.exchange"]
            .sudo()
            .search([("channel_id", "=", f"integration.receiver,{self.receiver.id}")])
        )

    def _record(self, **kwargs):
        self.receiver._record_inbound_exchange(
            method="post", path="/probe", remote_addr="203.0.113.1", **kwargs
        )

    def test_a_receiver_is_an_exchange_channel(self):
        models = dict(self.env["integration.exchange"]._selection_channel_models())

        self.assertIn("integration.receiver", models)

    def test_an_admitted_call_is_recorded_when_the_transaction_commits(self):
        self._record(body=b'{"event": "ping"}', event_type="ping")
        self.assertFalse(self._rows())

        self.env.cr.precommit.run()

        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.direction, "inbound")
        self.assertEqual(row.request_method, "POST")
        self.assertEqual(row.state, "success")
        self.assertEqual(row.event_type, "ping")
        self.assertEqual(json.loads(row.request_payload), {"event": "ping"})

    def test_a_secret_in_the_body_is_masked(self):
        self._record(body=json.dumps({"password": "hunter2", "id": 7}))

        self.env.cr.precommit.run()

        stored = json.loads(self._rows().request_payload)
        self.assertEqual(stored["id"], 7)
        self.assertNotEqual(stored["password"], "hunter2")

    def test_a_large_body_is_truncated_and_says_how_much(self):
        with patch.object(type(self.receiver), "_INBOUND_PAYLOAD_LOG_BYTES", 16):
            self._record(body="x" * 100)
            self.env.cr.precommit.run()

        row = self._rows()
        self.assertEqual(len(row.request_payload), 16)
        self.assertEqual(row.request_payload_omitted_bytes, 84)

    def test_a_large_json_body_keeps_a_masked_prefix_and_says_how_much(self):
        body = json.dumps({"password": "hunter2", "rows": list(range(5000))})
        with patch.object(type(self.receiver), "_INBOUND_PAYLOAD_LOG_BYTES", 64):
            self._record(body=body)
            self.env.cr.precommit.run()

        row = self._rows()
        self.assertEqual(len(row.request_payload), 64)
        self.assertTrue(row.request_payload.startswith('{"password": "***REDACTED***"'))
        self.assertEqual(row.request_payload_omitted_bytes, len(body) - 64)

    def test_the_head_of_an_omitted_body_is_masked(self):
        self.receiver.log_request_payload_max_bytes = 32
        body = '{"password": "hunter2", "audio": "' + "A" * 500 + '"}'

        head = json.loads(self.receiver._omitted_payload_vals(body)["request_payload"])[
            "_omitted"
        ]["head"]

        self.assertNotIn("hunter2", head)
        self.assertTrue(head.startswith('{"password": '))

    def test_a_failed_call_survives_the_rollback_it_caused(self):
        self._record(status_code=500, error="handler raised")

        cr = self.env.cr
        cr.clear()
        with self.enter_registry_test_mode():
            cr.postrollback.run()

        row = self._rows()
        self.assertEqual(row.state, "failed")
        self.assertEqual(row.error_message, "handler raised")

    def _admit(self, body=b'{"probe": 1}', event_type="probe"):
        return open_admission(self.receiver, body, event_type)

    def test_an_admitted_call_is_a_row_the_handler_can_settle(self):
        admission = self._admit()

        row = self._rows()
        self.assertEqual(admission.exchange, row)
        self.assertEqual(
            (row.state, row.event_type, row.request_method),
            ("processing", "probe", "POST"),
        )
        self.assertIn("probe", row.request_payload)
        self.assertEqual(row.request_payload_hash, admission.payload_hash)

        admission.settle("the handler could not")
        self.assertEqual(row.state, "failed")
        self.assertEqual(row.error_message, "the handler could not")

    def test_a_copy_inside_the_window_is_refused_on_its_own_row(self):
        from odoo.addons.integration.tools.admission import Refused

        self.receiver.write({"duplicate_detection_enabled": True})
        self._admit(b'{"probe": 1}')

        # not assertRaises: the test case's rolls back to a savepoint, and
        # the row the refusal leaves is what this test reads
        try:
            self._admit(b'{ "probe" : 1 }')
        except Refused as refused:
            self.assertEqual(
                (refused.status, refused.error_code), (409, "duplicate_event")
            )
            self.assertTrue(refused.commit, "the duplicate row is kept")
        else:
            self.fail("a copy inside the window was admitted")
        self.assertEqual(
            self._rows().sorted("id").mapped("state"), ["processing", "duplicate"]
        )

    def test_the_row_of_a_call_that_rolled_back_names_the_handler_s_last_word(self):
        admission = self._admit()
        admission.settle("OSError: connection reset")

        cr = self.env.cr
        cr.clear()
        with self.enter_registry_test_mode():
            cr.postrollback.run()

        rows = self._rows().sorted("id")
        kept = rows[-1]
        self.assertEqual(kept.state, "failed")
        self.assertEqual(kept.error_message, "OSError: connection reset")
        self.assertEqual(kept.event_type, "probe")

    def test_a_scheme_method_decides_for_its_auth_type(self):
        self.receiver.write(
            {
                "auth_type": "hmac_sha256",
                "credential_id": self.env["credential.credential"]
                .create(
                    {
                        "name": "Probe receiver secret",
                        "category_id": self.env.ref(
                            "credential.credential_category_custom"
                        ).id,
                        "credential_value": "probe-secret",
                    }
                )
                .id,
            }
        )
        calls = []

        def scheme(self, headers, body):
            calls.append(headers.get("X-Probe"))
            return headers.get("X-Probe") == "yes"

        with patch.object(
            type(self.receiver), "_authenticate_scheme_hmac_sha256", scheme, create=True
        ):
            self.assertTrue(self.receiver._authenticate_by_scheme({"X-Probe": "yes"}))
            self.assertFalse(self.receiver._authenticate_by_scheme({"X-Probe": "no"}))
        self.assertEqual(calls, ["yes", "no"])


@tagged("post_install", "-at_install", "integration")
class TestGateRow(TransactionCase):
    """What every gate does with the row it opens, receiver or not: names the
    event from the body, withholds a poll, keeps a withheld call's failure,
    takes the handler's annotations and stamps the duration."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.receiver = cls.env["integration.receiver"].create(
            {"name": "Gate probe", "code": "gate_probe", "auth_type": "none"}
        )

    def _rows(self):
        return (
            self.env["integration.exchange"]
            .sudo()
            .search([("channel_id", "=", f"integration.receiver,{self.receiver.id}")])
        )

    def test_the_body_names_the_event(self):
        def from_body(self, admission, event_type):
            return f"{event_type}:{admission.payload['kind']}"

        with patch.object(type(self.receiver), "_inbound_event_type", from_body):
            admission = open_admission(self.receiver, b'{"kind": "ping"}', "probe")

        self.assertEqual(admission.event_type, "probe:ping")
        self.assertEqual(self._rows().event_type, "probe:ping")

    def test_a_withheld_call_leaves_no_row_and_its_failure_leaves_one(self):
        with patch.object(
            type(self.receiver), "_inbound_event_logged", lambda self, event: False
        ):
            admission = open_admission(self.receiver)
            self.assertIsNone(admission.exchange)
            admission.annotate(user_id=self.env.user.id)
            admission.settle()
            self.env.cr.precommit.run()
            self.assertFalse(self._rows(), "a successful poll is not worth a row")

            admission.settle("the handler could not")
            self.env.cr.precommit.run()

        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(
            (row.state, row.error_message, row.event_type, row.user_id),
            ("failed", "the handler could not", "probe", self.env.user),
        )
        self.assertGreaterEqual(row.duration_ms, 0)

    def test_the_handler_annotates_the_row_and_settling_times_it(self):
        admission = open_admission(self.receiver)
        admission.annotate(user_id=self.env.user.id, origin_model="res.partner")
        admission.settle()

        row = admission.exchange
        self.assertEqual(
            (row.user_id, row.origin_model), (self.env.user, "res.partner")
        )
        self.assertEqual(row.state, "success")
        self.assertGreater(row.duration_ms, 0)

    def test_a_settled_error_is_masked(self):
        admission = open_admission(self.receiver)
        admission.settle("token=hunter2 refused")

        self.assertNotIn("hunter2", admission.exchange.error_message)

    def test_a_gate_s_own_retention_wins_over_the_default(self):
        from datetime import timedelta

        from odoo import fields

        self.env["ir.config_parameter"].sudo().set_param(
            "integration.log_retention_days", "90"
        )
        self.receiver.log_retention_days = 7
        first = open_admission(self.receiver)
        first.settle()
        old = first.exchange
        old.date_completed = fields.Datetime.now() - timedelta(days=30)
        recent = open_admission(self.receiver).exchange

        self.env["integration.exchange"]._gc_old_logs()

        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())


@tagged("post_install", "-at_install", "integration")
class TestExternalEventIds(TransactionCase):
    """A sender's own event id is claimed by the row: a redelivery is refused
    while the first is processing or once it succeeded, and admitted again
    after the first failed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.receiver = cls.env["integration.receiver"].create(
            {
                "name": "Id probe",
                "code": "id_probe",
                "auth_type": "none",
                "duplicate_detection_enabled": False,
            }
        )

    def _rows(self):
        return (
            self.env["integration.exchange"]
            .sudo()
            .search(
                [("channel_id", "=", f"integration.receiver,{self.receiver.id}")],
                order="id",
            )
        )

    def _admit(self, body):
        with patch.object(
            type(self.receiver),
            "_inbound_event_id",
            lambda self, admission, event: str(admission.payload.get("id")),
        ):
            return open_admission(self.receiver, body)

    def test_the_row_claims_the_id(self):
        admission = self._admit(b'{"id": 7, "n": 1}')
        self.assertEqual(admission.exchange.event_id_external, "7")

    def test_a_redelivery_is_refused_on_a_refusal_row_while_the_first_is_processing(
        self,
    ):
        from odoo.addons.integration.tools.admission import Refused

        self._admit(b'{"id": 7, "n": 1}')
        try:
            self._admit(b'{"id": 7, "n": 2}')
        except Refused as refused:
            self.assertEqual(
                (refused.status, refused.error_code, refused.commit),
                (409, "duplicate_event", True),
            )
        else:
            self.fail("a redelivery of a processing event was admitted")
        self.assertEqual(
            self._rows().mapped("state"), ["processing", "refused"], "the copy's row"
        )
        self.assertEqual(self._rows()[-1].refusal_reason, "duplicate_event")

    def test_a_redelivery_after_a_success_is_refused(self):
        from odoo.addons.integration.tools.admission import Refused

        self._admit(b'{"id": 8}').settle()
        with self.assertRaises(Refused):
            self._admit(b'{"id": 8}')

    def test_a_redelivery_after_a_failure_is_admitted(self):
        self._admit(b'{"id": 9}').settle("the handler could not")
        again = self._admit(b'{"id": 9}')
        self.assertEqual(again.exchange.state, "processing")
        self.assertEqual(self._rows().mapped("state"), ["failed", "processing"])

    def test_ids_are_per_channel(self):
        other = self.receiver.copy({"code": "id_probe_2", "name": "Other"})
        self._admit(b'{"id": 10}')
        with patch.object(
            type(other),
            "_inbound_event_id",
            lambda self, admission, event: str(admission.payload.get("id")),
        ):
            twin = open_admission(other, b'{"id": 10}')
        self.assertEqual(twin.exchange.event_id_external, "10")
