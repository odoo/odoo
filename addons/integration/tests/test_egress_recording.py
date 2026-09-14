from unittest.mock import MagicMock, patch

import requests

from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "integration")
class TestEgressRecording(TransactionCase):
    def _rows(self, purpose):
        self.env.flush_all()
        self.env.cr.precommit.run()
        return self.env["integration.exchange"].search(
            [("tags", "=", f"egress:{purpose}")], order="id desc"
        )

    def _send(self, purpose, **patched):
        with patch.object(GuardedSession, "request", **patched):
            return self.env["ir.egress"].request(
                "GET",
                "https://api.example.com/v1/items?api_key=s3cr3t-value",
                purpose=purpose,
            )

    def test_a_call_through_egress_leaves_an_exchange_row(self):
        self._send("probe_api", return_value=MagicMock(status_code=200))

        row = self._rows("probe_api")
        self.assertEqual(len(row), 1)
        self.assertEqual(row.channel_id._name, "integration.egress.purpose")
        self.assertEqual(row.channel_id.purpose, "probe_api")
        self.assertEqual((row.request_method, row.status_code), ("GET", 200))
        self.assertEqual((row.direction, row.state), ("outbound", "success"))
        self.assertNotIn("s3cr3t-value", row.request_url)
        self.assertFalse(row.request_payload)

    def test_a_keyword_call_reaches_the_session_as_keywords(self):
        with patch.object(
            GuardedSession, "request", return_value=MagicMock(status_code=200)
        ) as sent:
            session = self.env["ir.egress"].session(purpose="probe_api")
            session.request(method="POST", url="https://api.example.com/v1/rates")

        self.assertEqual(
            sent.call_args.kwargs,
            {"method": "POST", "url": "https://api.example.com/v1/rates"},
        )
        self.assertEqual(self._rows("probe_api").request_method, "POST")

    def test_repeated_calls_share_one_purpose_channel(self):
        for _ in range(2):
            self._send("probe_api", return_value=MagicMock(status_code=200))

        rows = self._rows("probe_api")
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({row.channel_id for row in rows}), 1)

    def test_a_refused_call_is_recorded_as_failed(self):
        self._send("probe_api", return_value=MagicMock(status_code=429))

        row = self._rows("probe_api")
        self.assertEqual((row.state, row.error_type), ("failed", "rate_limit"))

    def test_a_timeout_is_recorded_and_still_raised(self):
        with self.assertRaises(requests.Timeout):
            self._send("probe_api", side_effect=requests.Timeout("read timed out"))

        row = self._rows("probe_api")
        self.assertEqual((row.state, row.error_type), ("failed", "timeout"))

    def test_content_fetches_are_not_recorded(self):
        self._send("link_preview", return_value=MagicMock(status_code=200))

        self.assertFalse(self._rows("link_preview"))

    def test_the_integration_client_is_not_recorded_twice(self):
        self._send("integration:probe", return_value=MagicMock(status_code=200))

        self.assertFalse(self._rows("integration:probe"))
