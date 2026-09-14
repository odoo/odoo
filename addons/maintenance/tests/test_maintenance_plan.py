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
        cls.stage_new = cls.env.ref("maintenance.stage_0")
        cls.stage_repaired = cls.env.ref("maintenance.stage_3")
        cls.stage_scrap = cls.env.ref("maintenance.stage_4")
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
                "date_start": datetime(2026, 1, 31, 10),
                **vals,
            }
        )

    def _close_at(self, plan, moment, stage=None, request=None):
        request = request or plan._get_open_request()
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
                    "date_occurrence": datetime(2026, 1, 31, 10),
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

    def test_an_occurrence_moved_earlier_and_done_early_is_not_repeated(self):
        plan = self._plan()
        february = self._close_at(plan, "2026-01-31 12:00:00")
        february.schedule_date = datetime(2026, 2, 20, 10)
        march = self._close_at(plan, "2026-02-25 12:00:00")
        self.assertEqual(march.date_occurrence, datetime(2026, 3, 31, 10))

    def test_an_occurrence_moved_past_the_next_one_says_what_it_skipped(self):
        plan = self._plan()
        february = self._close_at(plan, "2026-01-31 12:00:00")
        february.schedule_date = datetime(2026, 4, 2, 10)
        messages = plan.message_ids
        april = self._close_at(plan, "2026-04-02 12:00:00")
        self.assertEqual(april.date_occurrence, datetime(2026, 4, 30, 10))
        self.assertTrue(
            (plan.message_ids - messages).filtered(lambda m: "skipped" in m.body)
        )

    def test_a_late_completion_skips_the_dates_it_missed_and_says_so(self):
        plan = self._plan()
        messages = plan.message_ids
        april = self._close_at(plan, "2026-03-15 12:00:00")
        self.assertEqual(april.schedule_date, datetime(2026, 3, 31, 10))
        skipped = plan.message_ids - messages
        self.assertEqual(len(skipped.filtered(lambda m: "skipped" in m.body)), 1)

    def test_a_technician_without_plan_rights_closes_a_late_request(self):
        plan = self._plan(user_id=self.technician.id)
        request = plan._get_open_request()
        self.assertFalse(plan.with_user(self.technician).has_access("write"))
        with freeze_time("2026-03-15 12:00:00"):
            request.with_user(self.technician).stage_id = self.stage_repaired
            self.env.flush_all()
        self.assertEqual(
            plan._get_open_request().date_occurrence, datetime(2026, 3, 31, 10)
        )

    def test_a_completion_plan_counts_from_the_day_it_was_done(self):
        plan = self._plan(repeat_anchor="completion")
        february = self._close_at(plan, "2026-02-10 16:00:00")
        self.assertEqual(february.schedule_date, datetime(2026, 3, 10, 10))
        march = self._close_at(plan, "2026-03-09 08:00:00")
        self.assertEqual(march.schedule_date, datetime(2026, 4, 9, 10))

    def test_a_completion_plan_counts_from_the_close_date_given(self):
        plan = self._plan(repeat_anchor="completion")
        request = plan._get_open_request()
        with freeze_time("2026-02-20 12:00:00"):
            request.write(
                {"stage_id": self.stage_repaired.id, "close_date": date(2026, 2, 16)}
            )
        self.assertEqual(
            plan._get_open_request().schedule_date, datetime(2026, 3, 16, 10)
        )

    def test_a_cancelled_occurrence_hands_over_to_the_next_one(self):
        plan = self._plan()
        request = plan._get_open_request()
        with freeze_time("2026-02-20 12:00:00"):
            request.archive_equipment_request()
        self.assertEqual(
            plan._get_open_request().schedule_date, datetime(2026, 2, 28, 10)
        )

    def test_cancelling_an_overdue_occurrence_does_not_open_one_in_the_past(self):
        plan = self._plan()
        request = plan._get_open_request()
        with freeze_time("2026-03-15 12:00:00"):
            request.archive_equipment_request()
        self.assertEqual(
            plan._get_open_request().schedule_date, datetime(2026, 3, 31, 10)
        )

    def test_only_the_first_closing_stage_opens_the_next_request(self):
        plan = self._plan()
        request = plan._get_open_request()
        with freeze_time("2026-01-31 12:00:00"):
            request.stage_id = self.stage_repaired
            request.stage_id = self.stage_scrap
        self.assertEqual(len(plan.request_ids), 2)

    def test_reopening_a_request_projects_the_series_once(self):
        plan = self._plan()
        first = plan._get_open_request()
        with freeze_time("2026-01-31 12:00:00"):
            first.stage_id = self.stage_repaired
            first.stage_id = self.stage_new
            requests = plan._get_open_requests()
            self.assertEqual(len(requests), 2)
            occurrences = requests.get_plan_occurrences(
                "2026-02-01 00:00:00", "2026-05-31 23:59:59"
            )
        self.assertEqual(list(occurrences), [requests[-1].id])

    def test_a_duplicated_request_leaves_the_plan(self):
        plan = self._plan()
        self.assertFalse(plan._get_open_request().copy().plan_id)

    def test_deleting_the_open_request_opens_the_next_one(self):
        plan = self._plan()
        with freeze_time("2026-02-10 12:00:00"):
            plan._get_open_request().unlink()
            self.assertEqual(
                plan._get_open_request().date_occurrence, datetime(2026, 2, 28, 10)
            )

    def test_the_next_request_keeps_what_the_last_one_carried(self):
        plan = self._plan()
        request = plan._get_open_request()
        request.write(
            {
                "instruction_type": "text",
                "instruction_text": "<p>Check the belts</p>",
                "owner_user_id": self.technician.id,
            }
        )
        successor = self._close_at(plan, "2026-01-31 12:00:00")
        self.assertIn("Check the belts", successor.instruction_text)
        self.assertEqual(successor.owner_user_id, self.technician)

    def test_an_until_plan_stops_after_its_local_end_date(self):
        plan = self._plan(
            repeat_unit="week",
            tz="America/Mexico_City",
            date_start=datetime(2026, 9, 1, 3),
            repeat_type="until",
            repeat_until=date(2026, 9, 7),
        )
        successor = self._close_at(plan, "2026-09-01 04:00:00")
        self.assertEqual(successor.schedule_date, datetime(2026, 9, 8, 3))
        self.assertFalse(self._close_at(plan, "2026-09-08 04:00:00"))

    def test_an_until_plan_needs_its_end_date(self):
        with self.assertRaises(ValidationError):
            self._plan(repeat_type="until")

    def test_a_plan_keeps_its_local_hour_across_daylight_saving(self):
        plan = self._plan(date_start=datetime(2026, 3, 15, 10), tz="Europe/Brussels")
        april = self._close_at(plan, "2026-03-15 12:00:00")
        self.assertEqual(april.schedule_date, datetime(2026, 4, 15, 9))

    def test_the_dates_do_not_depend_on_who_closes(self):
        dates = []
        for closer_tz in ("America/Mexico_City", "Asia/Tokyo"):
            plan = self._plan(
                name=closer_tz,
                tz="America/Mexico_City",
                date_start=datetime(2026, 1, 31, 2),
            )
            request = plan._get_open_request().with_context(tz=closer_tz)
            self._close_at(plan, "2026-04-01 12:00:00", request=request)
            dates.append(plan._get_open_request().date_occurrence)
        self.assertEqual(dates[0], dates[1])
        self.assertEqual(dates[0], datetime(2026, 5, 1, 2))

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

    def test_a_resumed_fixed_plan_does_not_repeat_work_done_early(self):
        plan = self._plan(date_start=datetime(2026, 4, 30, 10))
        plan.action_archive()
        with freeze_time("2026-04-05 12:00:00"):
            plan.request_ids.stage_id = self.stage_repaired
        with freeze_time("2026-04-10 12:00:00"):
            plan.action_unarchive()
        self.assertEqual(
            plan._get_open_request().date_occurrence, datetime(2026, 5, 30, 10)
        )

    def test_a_resumed_completion_plan_counts_from_its_local_close_day(self):
        plan = self._plan(
            repeat_anchor="completion",
            repeat_unit="week",
            tz="America/Mexico_City",
            date_start=datetime(2026, 3, 1, 2),
        )
        plan.action_archive()
        with freeze_time("2026-03-05 20:00:00"):
            plan.request_ids.write(
                {"stage_id": self.stage_repaired.id, "close_date": date(2026, 3, 5)}
            )
        with freeze_time("2026-03-06 12:00:00"):
            plan.action_unarchive()
        self.assertEqual(
            plan._get_open_request().date_occurrence, datetime(2026, 3, 13, 2)
        )

    def test_moving_the_first_occurrence_moves_the_untouched_open_request(self):
        with freeze_time("2026-01-20 12:00:00"):
            plan = self._plan()
            plan.date_start = datetime(2026, 2, 5, 10)
        self.assertEqual(
            plan._get_open_request().date_occurrence, datetime(2026, 2, 5, 10)
        )
        march = self._close_at(plan, "2026-02-05 12:00:00")
        self.assertEqual(march.date_occurrence, datetime(2026, 3, 5, 10))

    def test_the_calendar_reads_the_plan_occurrences_from_the_server(self):
        with freeze_time("2026-01-20 12:00:00"):
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

    def test_the_calendar_does_not_project_dates_already_missed(self):
        with freeze_time("2026-04-10 12:00:00"):
            plan = self._plan()
            request = plan._get_open_request()
            occurrences = request.get_plan_occurrences(
                "2026-02-01 00:00:00", "2026-05-31 23:59:59"
            )
        self.assertEqual(
            occurrences, {request.id: ["2026-04-30 10:00:00", "2026-05-31 10:00:00"]}
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
