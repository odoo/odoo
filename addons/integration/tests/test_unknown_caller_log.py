from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "integration")
class TestUnknownCallerLog(TransactionCase):
    """A call for a subject no channel answers for is a refused row with no
    channel, naming what the caller asked for; one row per caller per window."""

    def _rows(self, model="probe.receiver"):
        return self.env["integration.exchange"].search(
            [
                ("state", "=", "refused"),
                ("refusal_reason", "=", "endpoint_not_found"),
                ("channel_name", "like", f"{model}:%"),
            ]
        )

    def test_repeated_unknown_calls_from_one_caller_collapse_into_one_row(self):
        rows = self.env["integration.exchange"]

        for _ in range(3):
            rows._record_unknown_caller("probe.receiver", "id 42", "203.0.113.5")

        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.attempt_count, 3)
        self.assertEqual(row.status_code, 404)
        self.assertFalse(row.channel_id)
        self.assertEqual(row.channel_name, "probe.receiver: id 42")
        self.assertFalse(row.is_success)

    def test_each_caller_gets_its_own_row(self):
        rows = self.env["integration.exchange"]

        rows._record_unknown_caller("probe.receiver", "id 42", "203.0.113.5")
        rows._record_unknown_caller("probe.receiver", "id 43", "203.0.113.6")

        self.assertEqual(len(self._rows()), 2)

    def test_the_row_stays_append_only(self):
        self.env["integration.exchange"]._record_unknown_caller(
            "probe.receiver", "id 42", "203.0.113.5"
        )

        with self.assertRaises(UserError):
            self._rows().write({"error_message": "rewritten"})
        with self.assertRaises(UserError):
            self._rows().unlink()

    def test_a_row_names_its_channel_or_its_refusal(self):
        from psycopg.errors import CheckViolation

        with self.assertRaises(CheckViolation), self.env.cr.savepoint():
            self.env["integration.exchange"].create(
                {"direction": "inbound", "state": "failed"}
            )
