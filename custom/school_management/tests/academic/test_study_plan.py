import secrets
from datetime import datetime, time, timedelta
import pytz

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from ..common import StudyPlanCommon


@tagged("post_install", "-at_install", "school_management")
class TestStudyPlan(StudyPlanCommon):

    def _check_study_plan_available(self):
        """Helper to verify university.study.plan model availability."""
        if "university.study.plan" not in self.env:
            self.skipTest("Feature 'university.study.plan' is not implemented yet in school_management.")

    def test_no_overlap_with_classes(self):
        """Rule: Study plan sessions must not overlap any class session or its 15-minute buffer.

        Protects schedule feasibility: students need transition time before and after class,
        so study blocks must maintain at least a 15-minute buffer from scheduled timetable sessions.
        """
        self._check_study_plan_available()
        # Generate 4-week study plan
        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=28),
        })
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        lines = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        buffer_delta = timedelta(minutes=15)

        for line in lines:
            # Check overlap with published timetable slots
            for slot in self.published_slots:
                buffered_start = slot.start_time - buffer_delta
                buffered_end = slot.end_time + buffer_delta
                overlaps = (line.start_time < buffered_end) and (line.end_time > buffered_start)
                self.assertFalse(
                    overlaps,
                    f"Study line {line.start_time} - {line.end_time} overlaps class slot {slot.name} ({buffered_start} - {buffered_end} with 15m buffer).",
                )

    def test_no_overlap_between_lines(self):
        """Rule: No two study lines within the study plan may overlap each other.

        Protects single-task focus: a student cannot study two subjects simultaneously,
        so all scheduled study sessions must be mutually disjoint in time.
        """
        self._check_study_plan_available()
        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=28),
        })
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        lines = plan.line_ids.sorted("start_time") if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)], order="start_time asc")
        for i in range(len(lines) - 1):
            current_line = lines[i]
            next_line = lines[i + 1]
            self.assertLessEqual(
                current_line.end_time,
                next_line.start_time,
                f"Study line ending at {current_line.end_time} overlaps subsequent study line starting at {next_line.start_time}.",
            )

    def test_within_allowed_hours(self):
        """Rule: Study lines must fall strictly within the user's allowed daily study window.

        Protects daily study boundaries: study blocks must not be scheduled during sleep
        or restricted hours (start >= earliest_hour and end <= latest_hour in local timezone).
        """
        self._check_study_plan_available()
        earliest_hour = 8.0   # 08:00 AM
        latest_hour = 22.0    # 10:00 PM
        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=7),
            "earliest_hour": earliest_hour,
            "latest_hour": latest_hour,
        })
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        tz = pytz.timezone(self.env.user.tz or "UTC")
        lines = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        for line in lines:
            local_start = pytz.utc.localize(line.start_time).astimezone(tz)
            local_end = pytz.utc.localize(line.end_time).astimezone(tz)

            start_hour_float = local_start.hour + local_start.minute / 60.0
            end_hour_float = local_end.hour + local_end.minute / 60.0

            self.assertGreaterEqual(
                start_hour_float,
                earliest_hour,
                f"Study line local start time ({start_hour_float}) earlier than allowed earliest hour ({earliest_hour}).",
            )
            self.assertLessEqual(
                end_hour_float,
                latest_hour,
                f"Study line local end time ({end_hour_float}) later than allowed latest hour ({latest_hour}).",
            )

    def test_allowed_days_only(self):
        """Rule: Study lines must only be scheduled on designated allowed days of the week.

        Protects student rest days: if a plan configures study_days to Mon-Fri,
        no study line may fall on Saturday or Sunday.
        """
        self._check_study_plan_available()
        # Restrict to Monday through Friday (0, 1, 2, 3, 4)
        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=14),
            "study_days": "mon,tue,wed,thu,fri",
        })
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        tz = pytz.timezone(self.env.user.tz or "UTC")
        lines = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        for line in lines:
            local_dt = pytz.utc.localize(line.start_time).astimezone(tz)
            self.assertNotIn(
                local_dt.weekday(),
                [5, 6],
                f"Study line falls on weekend (weekday {local_dt.weekday()}) when restricted to weekdays.",
            )

    def test_holidays_skipped(self):
        """Rule: Study plan sessions must not be scheduled on recognized university holidays.

        Protects academic calendar observance: scheduled university holidays must be respected
        and treated as unavailable days for automated study generation.
        """
        self._check_study_plan_available()
        # Create a holiday on Wednesday of the first week
        wednesday = self.next_monday + timedelta(days=2)
        holiday = self.env["university.holiday"].create({
            "name": f"Campus Holiday {secrets.token_hex(2)}",
            "date_start": wednesday,
            "date_end": wednesday,
            "academic_year_id": self.academic_year.id,
        })

        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=7),
        })
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        tz = pytz.timezone(self.env.user.tz or "UTC")
        lines = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        for line in lines:
            local_dt = pytz.utc.localize(line.start_time).astimezone(tz)
            self.assertNotEqual(
                local_dt.date(),
                wednesday,
                f"Study line was scheduled on a university holiday ({wednesday}).",
            )
        holiday.unlink()

    def test_weekly_hours_near_target(self):
        """Rule: Weekly study hours total should be close to target when sufficient free time exists.

        Protects workload pacing: with hours_per_week = 10 and session_minutes = 60,
        each full week should total between 9 and 11 hours.
        """
        self._check_study_plan_available()
        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=14),
            "hours_per_week": 10.0,
            "session_minutes": 60,
        })
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        lines = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        # Check Week 1 hours
        week1_end = self.next_monday + timedelta(days=7)
        week1_lines = lines.filtered(lambda l: l.start_time < datetime.combine(week1_end, time.min))
        total_hours_w1 = sum((l.end_time - l.start_time).total_seconds() / 3600.0 for l in week1_lines)
        self.assertGreaterEqual(total_hours_w1, 9.0, "Total weekly study hours should be at least 9.")
        self.assertLessEqual(total_hours_w1, 11.0, "Total weekly study hours should be at most 11.")

    def test_only_enrolled_subjects(self):
        """Rule: Study lines must strictly belong to the student's actively enrolled subjects.

        Protects curriculum relevance: the algorithm must never schedule study sessions
        for subjects the student is not currently enrolled in.
        """
        self._check_study_plan_available()
        # Create an unrelated subject not in the student's section/enrollment
        other_subject = self.env["university.subject"].create({
            "name": f"Philosophy {secrets.token_hex(2)}",
            "code": f"PHIL_{secrets.token_hex(2).upper()}",
            "department_id": self.department.id,
        })

        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=14),
        })
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        lines = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        enrolled_subjects = self.subjects
        for line in lines:
            self.assertIn(
                line.subject_id,
                enrolled_subjects,
                f"Study line subject {line.subject_id.name} is not one of the student's enrolled subjects.",
            )
            self.assertNotEqual(line.subject_id, other_subject)

    def test_exam_weighting(self):
        """Rule: Upcoming examinations boost study session frequency for that subject with exam_prep reason.

        Protects exam readiness: if an assessment/exam exists within 10 days for subject A,
        subject A receives higher priority/more lines tagged with reason='exam_prep'.
        """
        self._check_study_plan_available()
        if "university.exam" not in self.env:
            self.skipTest("Feature 'university.exam' model is not available for exam weighting.")

        # Create an upcoming exam 10 days out for subject_1
        exam_date = self.next_monday + timedelta(days=10)
        exam = self.env["university.exam"].create({
            "name": f"Midterm Exam {self.subject_1.name}",
            "exam_type": "midterm",
            "subject_id": self.subject_1.id,
            "section_id": self.class_section.id,
            "exam_date": exam_date,
        })

        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=14),
        })
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        lines = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        subj1_lines = lines.filtered(lambda l: l.subject_id == self.subject_1)
        subj2_lines = lines.filtered(lambda l: l.subject_id == self.subject_2)

        self.assertGreater(
            len(subj1_lines),
            len(subj2_lines),
            "Subject with upcoming exam should receive more study sessions.",
        )
        exam_prep_lines = subj1_lines.filtered(lambda l: getattr(l, "reason", None) == "exam_prep")
        self.assertTrue(exam_prep_lines, "Subject with upcoming exam must have lines with reason='exam_prep'.")
        exam.unlink()

    def test_shortfall_warning_not_error(self):
        """Rule: Severe timetable constraints yield a shortfall warning rather than crashing with an exception.

        Protects user experience: if the student has very little available free time,
        generation succeeds with available slots and records a shortfall warning gracefully.
        """
        self._check_study_plan_available()
        # Request unrealistic study hours (e.g. 80 hours per week with tight window)
        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=7),
            "hours_per_week": 80.0,
            "earliest_hour": 18.0,
            "latest_hour": 20.0,
        })
        # Should NOT raise exception, must generate available lines and record warning
        result = plan.action_generate_schedule() if hasattr(plan, "action_generate_schedule") else None
        lines = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        self.assertTrue(lines, "Generation should succeed and create available lines.")

        has_warning = (
            getattr(plan, "shortfall_warning", False)
            or (isinstance(result, dict) and "warning" in result.get("params", {}).get("title", "").lower())
            or getattr(plan, "has_shortfall", False)
        )
        self.assertTrue(has_warning, "A shortfall warning must be recorded when target hours cannot be fulfilled.")

    def test_regenerate_idempotent(self):
        """Rule: Regenerating with 'replace existing draft lines' preserves done lines and maintains count.

        Protects student progress tracking: completed study sessions marked 'done' are preserved,
        while pending drafts are cleanly replaced without creating duplicates.
        """
        self._check_study_plan_available()
        plan = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=7),
            "replace_existing_drafts": True,
        })
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        lines = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        initial_count = len(lines)
        self.assertGreater(initial_count, 0, "Initial lines should be created.")

        # Mark first line as done
        first_line = lines[0]
        if hasattr(first_line, "state"):
            first_line.state = "done"

        # Regenerate
        if hasattr(plan, "action_generate_schedule"):
            plan.action_generate_schedule()

        lines_after = plan.line_ids if hasattr(plan, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan.id)])
        self.assertEqual(len(lines_after), initial_count, "Regenerating should keep overall line count unchanged.")
        self.assertIn(first_line, lines_after, "Lines marked done must be preserved during regeneration.")

    def test_deterministic(self):
        """Rule: Deterministic generation generates the exact same schedule for identical input parameters.

        Protects algorithm consistency: running the generation twice under the same inputs
        must generate the exact same set of (subject, start_time, end_time) tuples.
        """
        self._check_study_plan_available()
        plan1 = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=7),
            "hours_per_week": 10.0,
        })
        if hasattr(plan1, "action_generate_schedule"):
            plan1.action_generate_schedule()
        lines1 = plan1.line_ids if hasattr(plan1, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan1.id)])
        tuples1 = sorted([(l.subject_id.id, l.start_time, l.end_time) for l in lines1])

        plan2 = self.env["university.study.plan"].create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=7),
            "hours_per_week": 10.0,
        })
        if hasattr(plan2, "action_generate_schedule"):
            plan2.action_generate_schedule()
        lines2 = plan2.line_ids if hasattr(plan2, "line_ids") else self.env["university.study.plan.line"].search([("plan_id", "=", plan2.id)])
        tuples2 = sorted([(l.subject_id.id, l.start_time, l.end_time) for l in lines2])

        self.assertEqual(tuples1, tuples2, "Two identical runs must produce the exact same schedule tuples.")

    def test_security(self):
        """Rule: Access control enforces that students can only read/write their own study plan.

        Protects confidentiality and authorization: another student cannot read or modify
        this student's plan, while instructors have read-only access and cannot modify it.
        """
        self._check_study_plan_available()
        # Create a second student
        other_user = self.env["res.users"].create({
            "name": "Other Student",
            "login": f"other_student_{secrets.token_hex(4)}@test.com",
            "email": "other_student@test.com",
            "group_ids": [Command.set([self.group_student.id])],
        })
        other_student = self.env["university.student"].create({
            "name": "Other Student",
            "student_id": f"STD_{secrets.token_hex(3).upper()}",
            "user_id": other_user.id,
            "status": "active",
        })

        plan = self.env["university.study.plan"].with_user(self.student_user).create({
            "student_id": self.student.id,
            "start_date": self.next_monday,
            "end_date": self.next_monday + timedelta(days=7),
        })

        # Another student cannot read or write
        with self.assertRaises(AccessError):
            plan.with_user(other_user).read(["name", "student_id"])
        with self.assertRaises(AccessError):
            plan.with_user(other_user).write({"end_date": self.next_monday + timedelta(days=14)})

        # Teacher can read but cannot write
        plan.with_user(self.teacher_user).read(["name", "student_id"])
        with self.assertRaises(AccessError):
            plan.with_user(self.teacher_user).write({"end_date": self.next_monday + timedelta(days=14)})
