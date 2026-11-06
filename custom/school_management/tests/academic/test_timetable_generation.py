import secrets
from datetime import timedelta
import pytz

from odoo import Command
from odoo.tests import tagged
from ..common import StudyPlanCommon


@tagged("post_install", "-at_install", "school_management")
class TestTimetableGeneration(StudyPlanCommon):

    def test_subject_repeats_same_slot_every_week(self):
        """Rule: Each subject's sessions share the same weekday and local start time across all weeks.

        Protects schedule predictability: students and instructors require consistency where a subject
        meets at the same designated timeslot every week.
        """
        tz = pytz.timezone(self.env.user.tz or "UTC")
        # In setUpClass, cls.published_slots was generated for 4 weeks for cls.class_section
        slots = self.env["university.timetable.slot"].search([
            ("section_id", "=", self.class_section.id),
        ])
        self.assertTrue(slots, "Timetable slots should exist for the test section.")

        subjects = slots.mapped("subject_id")
        self.assertEqual(len(subjects), 3, "All 3 subjects should have generated slots.")

        for subject in subjects:
            subj_slots = slots.filtered(lambda s: s.subject_id == subject)
            self.assertEqual(len(subj_slots), 4, f"Subject {subject.name} should have 4 weekly sessions.")

            # Convert naive UTC start times to user's local timezone
            local_weekdays = set()
            local_start_times = set()
            for s in subj_slots:
                local_dt = pytz.utc.localize(s.start_time).astimezone(tz)
                local_weekdays.add(local_dt.weekday())
                local_start_times.add(local_dt.time())

            self.assertEqual(
                len(local_weekdays),
                1,
                f"Subject {subject.name} sessions must all fall on the same weekday across all 4 weeks.",
            )
            self.assertEqual(
                len(local_start_times),
                1,
                f"Subject {subject.name} sessions must all start at the same local time across all 4 weeks.",
            )

    def test_conflict_leaves_no_stray_rows(self):
        """Rule: A timeslot conflict during generation rolls back the entire series without orphan rows.

        Protects atomicity of timetable series creation: when a collision occurs in week N,
        any slots created in weeks 0..N-1 within that series must be rolled back, and the subject
        must either move to an alternative conflict-free timeslot or be cleanly reported as skipped.
        """
        Slot = self.env["university.timetable.slot"]
        teacher_conf = self.env["university.teacher"].create({
            "name": f"Teacher Conf {secrets.token_hex(2)}",
            "faculty_id": self.faculty.id,
            "department_id": self.department.id,
        })
        classroom_conf = self.env["university.classroom"].create({
            "name": f"Room Conf {secrets.token_hex(2)}",
            "capacity": 30,
        })
        test_sec = self.env["university.class.section"].create({
            "name": f"SEC_CONF_{secrets.token_hex(2).upper()}",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
            "teacher_id": teacher_conf.id,
            "classroom_id": classroom_conf.id,
            "capacity": 30,
        })

        # Use week 5..8 (so no interference with setUpClass 4-week sessions)
        start_date = self.next_monday + timedelta(days=28)
        # Week 2 within this 4-week window:
        conflict_monday = start_date + timedelta(days=14)
        conf_start, conf_end = self.slot_mon_1._datetime_for_week(conflict_monday, 0)

        # Pre-create a conflicting session blocking teacher_conf on slot_mon_1 only in week 2
        conflicting_slot = Slot.create({
            "teacher_id": teacher_conf.id,
            "section_id": self.class_section.id,
            "subject_id": self.subject_1.id,
            "classroom_id": self.classroom.id,
            "timeslot_id": self.slot_mon_1.id,
            "start_time": conf_start,
            "end_time": conf_end,
            "generation_state": "published",
        })

        # Run wizard for test_sec offering slot_mon_1 and slot_mon_2
        wizard = self.env["university.timetable.generation.wizard"].create({
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "section_ids": [Command.set([test_sec.id])],
            "timeslot_ids": [Command.set([self.slot_mon_1.id, self.slot_mon_2.id])],
            "start_date": start_date,
            "week_count": 4,
            "sessions_per_week": 1,
        })
        wizard.action_generate_timetable()

        # Slot generation on slot_mon_1 must have rolled back completely, leaving 0 partial rows
        partial_slots = Slot.search([
            ("section_id", "=", test_sec.id),
            ("timeslot_id", "=", self.slot_mon_1.id),
        ])
        self.assertEqual(
            len(partial_slots),
            0,
            "Slot series on conflicting timeslot must completely roll back, leaving 0 orphan rows.",
        )

        # Successful subjects must have all 4 weekly sessions (never a partial count like 1 or 2)
        for subj in self.subjects:
            sec_subj_slots = Slot.search([
                ("section_id", "=", test_sec.id),
                ("subject_id", "=", subj.id),
            ])
            self.assertIn(
                len(sec_subj_slots),
                [0, 4],
                f"Subject {subj.name} must either have all 4 weekly sessions or 0 (never a partial series).",
            )

        conflicting_slot.unlink()

    def test_generation_twice_no_crash(self):
        """Rule: Running timetable generation twice does not crash and produces no duplicates.

        Protects idempotency of generation: subsequent runs either replace existing drafts
        cleanly or skip gracefully without throwing uncaught database or integrity exceptions.
        """
        Slot = self.env["university.timetable.slot"]
        teacher_idemp = self.env["university.teacher"].create({
            "name": f"Teacher Idemp {secrets.token_hex(2)}",
            "faculty_id": self.faculty.id,
            "department_id": self.department.id,
        })
        classroom_idemp = self.env["university.classroom"].create({
            "name": f"Room Idemp {secrets.token_hex(2)}",
            "capacity": 30,
        })
        single_subj = self.env["university.subject"].create({
            "name": f"OS {secrets.token_hex(2)}",
            "code": f"OS_{secrets.token_hex(2).upper()}",
            "department_id": self.department.id,
        })
        single_sec = self.env["university.class.section"].create({
            "name": f"SEC_IDEMP_{secrets.token_hex(2).upper()}",
            "subject_id": single_subj.id,
            "semester_id": self.semester.id,
            "teacher_id": teacher_idemp.id,
            "classroom_id": classroom_idemp.id,
            "capacity": 30,
        })

        # Use week 5..6
        start_date = self.next_monday + timedelta(days=28)

        # First run: 2 weeks
        wizard1 = self.env["university.timetable.generation.wizard"].create({
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "section_ids": [Command.set([single_sec.id])],
            "timeslot_ids": [Command.set([self.slot_sat_1.id])],
            "start_date": start_date,
            "week_count": 2,
            "sessions_per_week": 1,
        })
        wizard1.action_generate_timetable()
        slots_after_first = Slot.search([("section_id", "=", single_sec.id)])
        self.assertEqual(len(slots_after_first), 2, "Initial generation should create 2 weekly slots.")

        # Second run with replace_existing_drafts = True
        wizard2 = self.env["university.timetable.generation.wizard"].create({
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "section_ids": [Command.set([single_sec.id])],
            "timeslot_ids": [Command.set([self.slot_sat_1.id])],
            "start_date": start_date,
            "week_count": 2,
            "sessions_per_week": 1,
            "replace_existing_drafts": True,
        })
        wizard2.action_generate_timetable()

        slots_after_second = Slot.search([("section_id", "=", single_sec.id)])
        self.assertEqual(len(slots_after_second), 2, "Regeneration with replacement should maintain slot count.")
        # Check no duplicates for (section, subject, start_time)
        unique_keys = set((s.section_id.id, s.subject_id.id, s.start_time) for s in slots_after_second)
        self.assertEqual(
            len(unique_keys),
            len(slots_after_second),
            "Duplicate (section, subject, start_time) slots must never exist.",
        )

    def test_timezone_correct(self):
        """Rule: Timeslot 08:00 start converts to exactly 08:00 local time in user's timezone.

        Protects timezone consistency: ensures stored UTC datetimes correctly reflect the
        intended wall-clock time in the configured user timezone (Asia/Phnom_Penh).
        """
        tz = pytz.timezone(self.env.user.tz or "UTC")
        # slot_mon_1 has start_hour = 8.0
        mon_slots = self.env["university.timetable.slot"].search([
            ("section_id", "=", self.class_section.id),
            ("timeslot_id", "=", self.slot_mon_1.id),
        ])
        self.assertTrue(mon_slots, "Should have slots generated for slot_mon_1 (08:00-09:30).")

        for slot in mon_slots:
            local_dt = pytz.utc.localize(slot.start_time).astimezone(tz)
            self.assertEqual(local_dt.hour, 8, "Local start hour must be 08:00.")
            self.assertEqual(local_dt.minute, 0, "Local start minute must be 00.")

    def test_start_date_tuesday(self):
        """Rule: Using a Tuesday start date still aligns session weekdays to the timeslot's day_of_week.

        Protects Monday-based week normalization: regardless of what day of the week the user
        inputs as start_date, the wizard aligns to the week's Monday so timeslot day_of_week matches.
        """
        tz = pytz.timezone(self.env.user.tz or "UTC")
        teacher_tue = self.env["university.teacher"].create({
            "name": f"Teacher Tue {secrets.token_hex(2)}",
            "faculty_id": self.faculty.id,
            "department_id": self.department.id,
        })
        classroom_tue = self.env["university.classroom"].create({
            "name": f"Room Tue {secrets.token_hex(2)}",
            "capacity": 30,
        })
        single_subj = self.env["university.subject"].create({
            "name": f"Compiler {secrets.token_hex(2)}",
            "code": f"CC_{secrets.token_hex(2).upper()}",
            "department_id": self.department.id,
        })
        tuesday_sec = self.env["university.class.section"].create({
            "name": f"SEC_TUE_{secrets.token_hex(2).upper()}",
            "subject_id": single_subj.id,
            "semester_id": self.semester.id,
            "teacher_id": teacher_tue.id,
            "classroom_id": classroom_tue.id,
            "capacity": 30,
        })

        tuesday_start = self.next_monday + timedelta(days=29)  # Week 5 Tuesday
        self.assertEqual(tuesday_start.weekday(), 1, "Verify test date is indeed a Tuesday.")

        wizard = self.env["university.timetable.generation.wizard"].create({
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "section_ids": [Command.set([tuesday_sec.id])],
            "timeslot_ids": [Command.set([self.slot_mon_1.id])],
            "start_date": tuesday_start,
            "week_count": 1,
            "sessions_per_week": 1,
        })
        wizard.action_generate_timetable()

        generated_slots = self.env["university.timetable.slot"].search([
            ("section_id", "=", tuesday_sec.id),
        ])
        self.assertTrue(generated_slots, "Slots should be generated with a Tuesday start date.")

        for slot in generated_slots:
            local_dt = pytz.utc.localize(slot.start_time).astimezone(tz)
            expected_weekday = int(slot.timeslot_id.day_of_week)
            self.assertEqual(
                local_dt.weekday(),
                expected_weekday,
                f"Generated slot weekday ({local_dt.weekday()}) must match timeslot day_of_week ({expected_weekday}).",
            )

    def test_publish_workflow(self):
        """Rule: Draft sessions are invisible to students; published sessions are visible.

        Protects security access rules: student timetable record rule restricts read access
        strictly to sessions where generation_state == 'published'.
        """
        # Create a draft slot in week 5 (free from setUpClass sessions)
        week5_monday = self.next_monday + timedelta(days=28)
        monday_dt, monday_end = self.slot_mon_1._datetime_for_week(week5_monday, 0)
        draft_slot = self.env["university.timetable.slot"].create({
            "teacher_id": self.teacher.id,
            "section_id": self.class_section.id,
            "subject_id": self.subject_1.id,
            "classroom_id": self.classroom.id,
            "timeslot_id": self.slot_mon_1.id,
            "start_time": monday_dt,
            "end_time": monday_end,
            "generation_state": "draft",
        })

        # Search as the student user
        visible_draft = self.env["university.timetable.slot"].with_user(self.student_user).search([
            ("id", "=", draft_slot.id),
        ])
        self.assertEqual(len(visible_draft), 0, "Draft timetable session must NOT be visible to student.")

        # Publish the slot
        draft_slot.action_publish()
        self.assertEqual(draft_slot.generation_state, "published")

        # Search again as student user
        visible_published = self.env["university.timetable.slot"].with_user(self.student_user).search([
            ("id", "=", draft_slot.id),
        ])
        self.assertEqual(len(visible_published), 1, "Published timetable session must BE visible to enrolled student.")
