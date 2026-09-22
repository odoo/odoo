from odoo.tests.common import TransactionCase


class TestWorkEntryTypeTracking(TransactionCase):
    """A work entry type is payroll configuration: its code names the salary
    rule and its rate weights it. Changing either has to leave a trace."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.work_entry_type = cls.env["hr.work.entry.type"].create(
            {"name": "Night shift", "code": "TRACK100", "amount_rate": 1.0}
        )
        # `create` ends on `_track_discard`, which parks a None against the new
        # id in the precommit batch. Left there, it makes every write in the
        # same unflushed transaction record nothing at all.
        cls.flush_tracking(cls.env)

    @staticmethod
    def flush_tracking(env):
        """Tracking values are built by a precommit callback, so flushing the
        ORM is not enough to see them: the cursor has to flush too."""
        env.flush_all()
        env.cr.flush()

    def _tracked(self, field_name):
        self.flush_tracking(self.env)
        return self.work_entry_type.message_ids.tracking_value_ids.filtered(
            lambda value: value.field_id.name == field_name
        )

    def test_rate_change_is_traced(self):
        self.work_entry_type.amount_rate = 2.0
        tracking = self._tracked("amount_rate")
        self.assertEqual(len(tracking), 1)
        self.assertEqual(tracking.old_value_float, 1.0)
        self.assertEqual(tracking.new_value_float, 2.0)

    def test_payroll_code_change_is_traced(self):
        self.work_entry_type.code = "TRACK200"
        tracking = self._tracked("code")
        self.assertEqual(len(tracking), 1)
        self.assertEqual(tracking.old_value_char, "TRACK100")
        self.assertEqual(tracking.new_value_char, "TRACK200")

    def test_time_off_flag_change_is_traced(self):
        """``is_leave`` decides whether the hours are work time at all."""
        self.work_entry_type.is_leave = True
        self.assertEqual(len(self._tracked("is_leave")), 1)

    def test_the_type_carries_a_chatter(self):
        self.assertIn(
            "chatter",
            self.env.ref("hr_work_entry.hr_work_entry_type_view_form").arch,
            "the trace is only useful where a user can read it",
        )
