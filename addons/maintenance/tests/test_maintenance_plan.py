from datetime import date, datetime

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestMaintenancePlan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tz="UTC"))
        cls.Plan = cls.env["maintenance.plan"]
        cls.technician = cls.env["res.users"].create(
            {
                "name": "Plan technician",
                "login": "plan_technician",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def _plan(self, **vals):
        return self.Plan.create(
            {
                "name": "Plan probe",
                "repeat_interval": 1,
                "repeat_unit": "month",
                "tz": "UTC",
                "date_first_occurrence": datetime(2026, 1, 31, 10),
                **vals,
            }
        )

    def _close_at(self, plan, moment, order=None):
        order = order or plan._get_open_order()
        with freeze_time(moment):
            order.action_done()
            self.env.flush_all()
        return plan._get_open_order()

    def test_a_plan_opens_its_first_order_on_its_first_occurrence(self):
        plan = self._plan(user_id=self.env.user.id, duration=3)
        self.assertRecordValues(
            plan.order_ids,
            [
                {
                    "name": "Plan probe",
                    "maintenance_type": "preventive",
                    "date_scheduled_start": datetime(2026, 1, 31, 10),
                    "date_plan_slot": datetime(2026, 1, 31, 10),
                    "user_id": self.env.user.id,
                    "duration": 3,
                    "state": "confirmed",
                }
            ],
        )
        self.assertEqual(plan.date_next_scheduled, datetime(2026, 1, 31, 10))

    def test_a_linked_order_stands_in_for_the_first_one(self):
        order = self.env["maintenance.order"].create(
            {"name": "Existing", "date_scheduled_start": datetime(2026, 2, 3, 10)}
        )
        plan = self._plan(order_ids=[(4, order.id)])
        self.assertEqual(plan.order_ids, order)

    def test_fixed_dates_come_back_to_the_month_end(self):
        plan = self._plan()
        february = self._close_at(plan, "2026-01-31 12:00:00")
        self.assertEqual(february.date_scheduled_start, datetime(2026, 2, 28, 10))
        march = self._close_at(plan, "2026-02-28 12:00:00")
        self.assertEqual(march.date_scheduled_start, datetime(2026, 3, 31, 10))
        self.assertEqual(plan.date_last_done, date(2026, 2, 28))

    def test_fixed_dates_ignore_a_rescheduled_occurrence(self):
        plan = self._plan()
        february = self._close_at(plan, "2026-01-31 12:00:00")
        february.date_scheduled_start = datetime(2026, 3, 3, 10)
        march = self._close_at(plan, "2026-03-03 12:00:00")
        self.assertEqual(march.date_scheduled_start, datetime(2026, 3, 31, 10))

    def test_an_occurrence_moved_earlier_and_done_early_is_not_repeated(self):
        plan = self._plan()
        february = self._close_at(plan, "2026-01-31 12:00:00")
        february.date_scheduled_start = datetime(2026, 2, 20, 10)
        march = self._close_at(plan, "2026-02-25 12:00:00")
        self.assertEqual(march.date_plan_slot, datetime(2026, 3, 31, 10))

    def test_an_occurrence_moved_past_the_next_one_says_what_it_skipped(self):
        plan = self._plan()
        february = self._close_at(plan, "2026-01-31 12:00:00")
        february.date_scheduled_start = datetime(2026, 4, 2, 10)
        messages = plan.message_ids
        april = self._close_at(plan, "2026-04-02 12:00:00")
        self.assertEqual(april.date_plan_slot, datetime(2026, 4, 30, 10))
        self.assertTrue(
            (plan.message_ids - messages).filtered(lambda m: "skipped" in m.body)
        )

    def test_a_late_completion_skips_the_dates_it_missed_and_says_so(self):
        plan = self._plan()
        messages = plan.message_ids
        april = self._close_at(plan, "2026-03-15 12:00:00")
        self.assertEqual(april.date_scheduled_start, datetime(2026, 3, 31, 10))
        skipped = plan.message_ids - messages
        self.assertEqual(len(skipped.filtered(lambda m: "skipped" in m.body)), 1)

    def test_a_technician_without_plan_rights_closes_a_late_order(self):
        plan = self._plan(user_id=self.technician.id)
        order = plan._get_open_order()
        self.assertFalse(plan.with_user(self.technician).has_access("write"))
        with freeze_time("2026-03-15 12:00:00"):
            order.with_user(self.technician).action_done()
            self.env.flush_all()
        self.assertEqual(
            plan._get_open_order().date_plan_slot, datetime(2026, 3, 31, 10)
        )

    def test_a_completion_plan_counts_from_the_day_it_was_done(self):
        plan = self._plan(repeat_anchor="completion")
        february = self._close_at(plan, "2026-02-10 16:00:00")
        self.assertEqual(february.date_scheduled_start, datetime(2026, 3, 10, 10))
        march = self._close_at(plan, "2026-03-09 08:00:00")
        self.assertEqual(march.date_scheduled_start, datetime(2026, 4, 9, 10))

    def test_a_completion_plan_counts_from_the_close_date_given(self):
        plan = self._plan(repeat_anchor="completion")
        order = plan._get_open_order()
        with freeze_time("2026-02-20 12:00:00"):
            order.write({"state": "done", "date_done": date(2026, 2, 16)})
        self.assertEqual(
            plan._get_open_order().date_scheduled_start, datetime(2026, 3, 16, 10)
        )

    def test_a_cancelled_occurrence_hands_over_to_the_next_one(self):
        plan = self._plan()
        order = plan._get_open_order()
        with freeze_time("2026-02-20 12:00:00"):
            order.action_cancel()
        self.assertEqual(
            plan._get_open_order().date_scheduled_start, datetime(2026, 2, 28, 10)
        )

    def test_cancelling_an_overdue_occurrence_does_not_open_one_in_the_past(self):
        plan = self._plan()
        order = plan._get_open_order()
        with freeze_time("2026-03-15 12:00:00"):
            order.action_cancel()
        self.assertEqual(
            plan._get_open_order().date_scheduled_start, datetime(2026, 3, 31, 10)
        )

    def test_closing_an_order_twice_opens_the_next_one_once(self):
        plan = self._plan()
        order = plan._get_open_order()
        with freeze_time("2026-01-31 12:00:00"):
            order.action_done()
            order.write({"state": "done"})
        self.assertEqual(len(plan.order_ids), 2)

    def test_reopening_an_order_projects_the_series_once(self):
        plan = self._plan()
        first = plan._get_open_order()
        with freeze_time("2026-01-31 12:00:00"):
            first.action_cancel()
            first.action_draft()
            orders = plan._get_open_orders()
            self.assertEqual(len(orders), 2)
            occurrences = orders.get_plan_occurrences(
                "2026-02-01 00:00:00", "2026-05-31 23:59:59"
            )
        self.assertEqual(list(occurrences), [orders[-1].id])

    def test_a_duplicated_order_leaves_the_plan(self):
        plan = self._plan()
        self.assertFalse(plan._get_open_order().copy().plan_id)

    def test_deleting_the_open_order_opens_the_next_one(self):
        plan = self._plan()
        with freeze_time("2026-02-10 12:00:00"):
            order = plan._get_open_order()
            order.action_draft()
            order.unlink()
            self.assertEqual(
                plan._get_open_order().date_plan_slot, datetime(2026, 2, 28, 10)
            )

    def test_the_next_order_keeps_what_the_last_one_carried(self):
        plan = self._plan()
        order = plan._get_open_order()
        order.write(
            {
                "instruction_type": "text",
                "instruction_text": "<p>Check the belts</p>",
            }
        )
        successor = self._close_at(plan, "2026-01-31 12:00:00")
        self.assertIn("Check the belts", successor.instruction_text)

    def test_an_until_plan_stops_after_its_local_end_date(self):
        plan = self._plan(
            repeat_unit="week",
            tz="America/Mexico_City",
            date_first_occurrence=datetime(2026, 9, 1, 3),
            repeat_type="until",
            repeat_until=date(2026, 9, 7),
        )
        successor = self._close_at(plan, "2026-09-01 04:00:00")
        self.assertEqual(successor.date_scheduled_start, datetime(2026, 9, 8, 3))
        self.assertFalse(self._close_at(plan, "2026-09-08 04:00:00"))

    def test_an_until_plan_needs_its_end_date(self):
        with self.assertRaises(ValidationError):
            self._plan(repeat_type="until")

    def test_a_plan_keeps_its_local_hour_across_daylight_saving(self):
        plan = self._plan(
            date_first_occurrence=datetime(2026, 3, 15, 10), tz="Europe/Brussels"
        )
        april = self._close_at(plan, "2026-03-15 12:00:00")
        self.assertEqual(april.date_scheduled_start, datetime(2026, 4, 15, 9))

    def test_the_dates_do_not_depend_on_who_closes(self):
        dates = []
        for closer_tz in ("America/Mexico_City", "Asia/Tokyo"):
            plan = self._plan(
                name=closer_tz,
                tz="America/Mexico_City",
                date_first_occurrence=datetime(2026, 1, 31, 2),
            )
            order = plan._get_open_order().with_context(tz=closer_tz)
            self._close_at(plan, "2026-04-01 12:00:00", order=order)
            dates.append(plan._get_open_order().date_plan_slot)
        self.assertEqual(dates[0], dates[1])
        self.assertEqual(dates[0], datetime(2026, 5, 1, 2))

    def test_an_archived_plan_opens_nothing_and_resumes_on_its_dates(self):
        plan = self._plan()
        plan.action_archive()
        with freeze_time("2026-01-31 12:00:00"):
            plan.order_ids.action_done()
        self.assertFalse(plan._get_open_order())
        with freeze_time("2026-04-10 12:00:00"):
            plan.action_unarchive()
        self.assertEqual(
            plan._get_open_order().date_scheduled_start, datetime(2026, 4, 30, 10)
        )

    def test_a_resumed_fixed_plan_does_not_repeat_work_done_early(self):
        plan = self._plan(date_first_occurrence=datetime(2026, 4, 30, 10))
        plan.action_archive()
        with freeze_time("2026-04-05 12:00:00"):
            plan.order_ids.action_done()
        with freeze_time("2026-04-10 12:00:00"):
            plan.action_unarchive()
        self.assertEqual(
            plan._get_open_order().date_plan_slot, datetime(2026, 5, 30, 10)
        )

    def test_a_resumed_completion_plan_counts_from_its_local_close_day(self):
        plan = self._plan(
            repeat_anchor="completion",
            repeat_unit="week",
            tz="America/Mexico_City",
            date_first_occurrence=datetime(2026, 3, 1, 2),
        )
        plan.action_archive()
        with freeze_time("2026-03-05 20:00:00"):
            plan.order_ids.write({"state": "done", "date_done": date(2026, 3, 5)})
        with freeze_time("2026-03-06 12:00:00"):
            plan.action_unarchive()
        self.assertEqual(
            plan._get_open_order().date_plan_slot, datetime(2026, 3, 13, 2)
        )

    def test_moving_the_first_occurrence_moves_the_untouched_open_order(self):
        with freeze_time("2026-01-20 12:00:00"):
            plan = self._plan()
            plan.date_first_occurrence = datetime(2026, 2, 5, 10)
        self.assertEqual(
            plan._get_open_order().date_plan_slot, datetime(2026, 2, 5, 10)
        )
        march = self._close_at(plan, "2026-02-05 12:00:00")
        self.assertEqual(march.date_plan_slot, datetime(2026, 3, 5, 10))

    def test_the_calendar_reads_the_plan_occurrences_from_the_server(self):
        with freeze_time("2026-01-20 12:00:00"):
            plan = self._plan()
            order = plan._get_open_order()
            occurrences = order.get_plan_occurrences(
                "2026-02-01 00:00:00", "2026-05-31 23:59:59"
            )
        self.assertEqual(
            occurrences,
            {
                order.id: [
                    "2026-02-28 10:00:00",
                    "2026-03-31 10:00:00",
                    "2026-04-30 10:00:00",
                    "2026-05-31 10:00:00",
                ]
            },
        )

    def test_the_calendar_does_not_project_dates_already_missed(self):
        with freeze_time("2026-04-10 12:00:00"):
            plan = self._plan()
            order = plan._get_open_order()
            occurrences = order.get_plan_occurrences(
                "2026-02-01 00:00:00", "2026-05-31 23:59:59"
            )
        self.assertEqual(
            occurrences, {order.id: ["2026-04-30 10:00:00", "2026-05-31 10:00:00"]}
        )

    def test_the_plan_takes_its_recurrence_vocabulary_from_the_mixin(self):
        self.assertEqual(
            self.Plan._fields["repeat_unit"].selection,
            self.env["mixin.recurrence.rule"]._fields["repeat_unit"].selection,
        )
        self.assertTrue(self.Plan._fields["repeat_unit"].required)
        for interval in (-1, 0):
            with self.assertRaises(ValidationError):
                self._plan(repeat_interval=interval)
