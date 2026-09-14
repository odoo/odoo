from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "integration")
class TestUnknownCallerLog(TransactionCase):
    def _rows(self, model="probe.receiver"):
        return self.env["inbound.access.log"].search(
            [("gate_model", "=", model), ("outcome", "=", "unknown_receiver")]
        )

    def test_repeated_unknown_calls_from_one_caller_collapse_into_one_row(self):
        log = self.env["inbound.access.log"]

        for _ in range(3):
            log._record_unknown_caller("probe.receiver", "id 42", "203.0.113.5")

        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.attempt_count, 3)
        self.assertEqual(row.status_code, 404)
        self.assertFalse(row.allowed)
        self.assertEqual(row.gate_id, 0)

    def test_each_caller_gets_its_own_row(self):
        log = self.env["inbound.access.log"]

        log._record_unknown_caller("probe.receiver", "id 42", "203.0.113.5")
        log._record_unknown_caller("probe.receiver", "id 43", "203.0.113.6")

        self.assertEqual(len(self._rows()), 2)

    def test_the_row_stays_append_only(self):
        self.env["inbound.access.log"]._record_unknown_caller(
            "probe.receiver", "id 42", "203.0.113.5"
        )

        with self.assertRaises(UserError):
            self._rows().write({"reason": "rewritten"})
