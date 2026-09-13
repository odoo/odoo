from datetime import timedelta

from odoo.exceptions import ValidationError

from .test_queued_dispatch import QueuedCase


class TestStepValidity(QueuedCase):
    def test_a_step_run_after_its_validity_is_skipped_with_a_reason(self):
        offer = self._action(
            "offer",
            "record.write({'ref': 'offered'})",
            validity_delay=1,
            validity_unit="hour",
        )
        (runtime,) = self._launch(self.partner)
        line = self._line(runtime, offer)
        line.date_ready -= timedelta(hours=2)

        self._dispatch()

        self.assertEqual(line.state, "skipped")
        self.assertIn("validity", line.error_message)
        self.assertEqual(runtime.state, "done")
        self.partner.invalidate_recordset(["ref"])
        self.assertFalse(self.partner.ref)

    def test_a_step_run_within_its_validity_runs(self):
        offer = self._action("offer", validity_delay=1, validity_unit="hour")
        (runtime,) = self._launch(self.partner)

        self._dispatch()

        self.assertEqual(self._line(runtime, offer).state, "done")

    def test_a_ready_step_records_when_it_became_ready(self):
        first = self._action("first")
        (runtime,) = self._launch(self.partner)

        self.assertTrue(self._line(runtime, first).date_ready)

    def test_a_negative_validity_is_refused(self):
        with self.assertRaises(ValidationError):
            self._action("offer", validity_delay=-1)
