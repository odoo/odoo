from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestMaintenancePlan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tz="UTC"))
        cls.Plan = cls.env["maintenance.plan"]
        cls.stage_new = cls.env.ref("maintenance.stage_0")
        cls.stage_repaired = cls.env.ref("maintenance.stage_3")
        cls.stage_scrap = cls.env.ref("maintenance.stage_4")

    def _plan(self, **vals):
        return self.Plan.create(
            {
                "name": "Plan probe",
                "repeat_interval": 1,
                "repeat_unit": "month",
                "date_start": datetime(2026, 1, 31, 10),
                **vals,
            }
        )

    def _close_at(self, plan, moment, stage=None):
        request = plan._get_open_request()
        with freeze_time(moment):
            request.stage_id = stage or self.stage_repaired
            self.env.flush_all()
        return plan._get_open_request()

    def test_a_plan_opens_its_first_request_on_its_first_occurrence(self):
        plan = self._plan(user_id=self.env.user.id, duration=3)
        self.assertRecordValues(
            plan.request_ids,
            [
                {
                    "name": "Plan probe",
                    "maintenance_type": "preventive",
                    "schedule_date": datetime(2026, 1, 31, 10),
                    "user_id": self.env.user.id,
                    "duration": 3,
                    "stage_id": self.stage_new.id,
                }
            ],
        )
        self.assertEqual(plan.date_next, datetime(2026, 1, 31, 10))

    def test_a_linked_request_stands_in_for_the_first_one(self):
        request = self.env["maintenance.request"].create(
            {"name": "Existing", "schedule_date": datetime(2026, 2, 3, 10)}
        )
        plan = self._plan(request_ids=[(4, request.id)])
        self.assertEqual(plan.request_ids, request)

    def test_fixed_dates_come_back_to_the_month_end(self):
        plan = self._plan()
        february = self._close_at(plan, "2026-01-31 12:00:00")
        self.assertEqual(february.schedule_date, datetime(2026, 2, 28, 10))
        march = self._close_at(plan, "2026-02-28 12:00:00")
        self.assertEqual(march.schedule_date, datetime(2026, 3, 31, 10))
        self.assertEqual(plan.date_last_done, date(2026, 2, 28))

    def test_fixed_dates_ignore_a_rescheduled_occurrence(self):
        plan = self._plan()
        february = self._close_at(plan, "2026-01-31 12:00:00")
        february.schedule_date = datetime(2026, 3, 3, 10)
        march = self._close_at(plan, "2026-03-03 12:00:00")
        self.assertEqual(march.schedule_date, datetime(2026, 3, 31, 10))

    def test_a_late_completion_skips_the_dates_it_missed_and_says_so(self):
        plan = self._plan()
        messages = plan.message_ids
        april = self._close_at(plan, "2026-03-15 12:00:00")
        self.assertEqual(april.schedule_date, datetime(2026, 3, 31, 10))
        skipped = plan.message_ids - messages
        self.assertEqual(len(skipped.filtered(lambda m: "skipped" in m.body)), 1)

    def test_a_completion_plan_counts_from_the_day_it_was_done(self):
        plan = self._plan(repeat_anchor="completion")
        february = self._close_at(plan, "2026-02-10 16:00:00")
        self.assertEqual(february.schedule_date, datetime(2026, 3, 10, 10))
        march = self._close_at(plan, "2026-03-09 08:00:00")
        self.assertEqual(march.schedule_date, datetime(2026, 4, 9, 10))

    def test_a_cancelled_occurrence_hands_over_to_the_next_one(self):
        plan = self._plan()
        request = plan._get_open_request()
        with freeze_time("2026-02-20 12:00:00"):
            request.archive_equipment_request()
        self.assertEqual(
            plan._get_open_request().schedule_date, datetime(2026, 2, 28, 10)
        )

    def test_only_the_first_closing_stage_opens_the_next_request(self):
        plan = self._plan()
        request = plan._get_open_request()
        with freeze_time("2026-01-31 12:00:00"):
            request.stage_id = self.stage_repaired
            request.stage_id = self.stage_scrap
        self.assertEqual(len(plan.request_ids), 2)

    def test_an_until_plan_stops_after_its_local_end_date(self):
        plan = self._plan(
            repeat_unit="week",
            date_start=datetime(2026, 9, 1, 3),
            repeat_type="until",
            repeat_until=date(2026, 9, 7),
        ).with_context(tz="America/Mexico_City")
        successor = self._close_at(plan, "2026-09-01 04:00:00")
        self.assertEqual(successor.schedule_date, datetime(2026, 9, 8, 3))
        self.assertFalse(self._close_at(plan, "2026-09-08 04:00:00"))

    def test_an_until_plan_needs_its_end_date(self):
        with self.assertRaises(ValidationError):
            self._plan(repeat_type="until")

    def test_a_plan_keeps_its_local_hour_across_daylight_saving(self):
        plan = self._plan(date_start=datetime(2026, 3, 15, 10)).with_context(
            tz="Europe/Brussels"
        )
        april = self._close_at(plan, "2026-03-15 12:00:00")
        self.assertEqual(april.schedule_date, datetime(2026, 4, 15, 9))

    def test_an_archived_plan_opens_nothing_and_resumes_on_its_dates(self):
        plan = self._plan()
        plan.action_archive()
        with freeze_time("2026-01-31 12:00:00"):
            plan.request_ids.stage_id = self.stage_repaired
        self.assertFalse(plan._get_open_request())
        with freeze_time("2026-04-10 12:00:00"):
            plan.action_unarchive()
        self.assertEqual(
            plan._get_open_request().schedule_date, datetime(2026, 4, 30, 10)
        )

    def test_the_calendar_reads_the_plan_occurrences_from_the_server(self):
        plan = self._plan()
        request = plan._get_open_request()
        occurrences = request.get_plan_occurrences(
            "2026-02-01 00:00:00", "2026-05-31 23:59:59"
        )
        self.assertEqual(
            occurrences,
            {
                request.id: [
                    "2026-02-28 10:00:00",
                    "2026-03-31 10:00:00",
                    "2026-04-30 10:00:00",
                    "2026-05-31 10:00:00",
                ]
            },
        )

    def test_the_plan_takes_its_recurrence_vocabulary_from_the_mixin(self):
        self.assertEqual(
            self.Plan._fields["repeat_unit"].selection,
            self.env["mixin.recurrence.rule"]._fields["repeat_unit"].selection,
        )
        for interval in (-1, 0):
            with self.assertRaises(ValidationError):
                self._plan(repeat_interval=interval)

    def test_moving_a_plan_start_later_moves_its_next_dates(self):
        plan = self._plan()
        plan.date_start = datetime(2026, 1, 31, 10) + relativedelta(days=5)
        february = self._close_at(plan, "2026-01-31 12:00:00")
        self.assertEqual(february.schedule_date, datetime(2026, 2, 5, 10))
