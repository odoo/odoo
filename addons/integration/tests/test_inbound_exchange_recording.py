import json
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


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

    def test_a_failed_call_survives_the_rollback_it_caused(self):
        self._record(status_code=500, error="handler raised")

        cr = self.env.cr
        cr.clear()
        with self.enter_registry_test_mode():
            cr.postrollback.run()

        row = self._rows()
        self.assertEqual(row.state, "failed")
        self.assertEqual(row.error_message, "handler raised")

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
