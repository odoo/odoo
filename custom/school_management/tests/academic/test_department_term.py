from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestDepartmentTerm(TransactionCase):
    def setUp(self):
        super().setUp()
        self.AcademicYear = self.env["university.academic.year"]
        self.Semester = self.env["university.semester"]
        self.DepartmentTerm = self.env["university.department.term"]
        self.Faculty = self.env["university.faculty"]
        self.Department = self.env["university.department"]
        self.Subject = self.env["university.subject"]
        self.SemesterSubject = self.env["university.semester.subject"]
        self.Holiday = self.env["university.holiday"]
        self.RolloverWizard = self.env["university.year.rollover.wizard"]
        self.Program = self.env["university.program"]
        self.Student = self.env["university.student"]
        self.Enrollment = self.env["university.enrollment"]

        self.academic_year = self.AcademicYear.create(
            {
                "name": "Department Term Test Academic Year",
                "date_start": "2026-01-01",
                "date_end": "2026-12-31",
            }
        )
        self.semester = self.Semester.create(
            {
                "name": "Department Term Test Semester",
                "academic_year_id": self.academic_year.id,
                "semester_type": "semester_1",
                "date_start": "2026-01-01",
                "date_end": "2026-06-30",
            }
        )
        self.faculty = self.Faculty.create(
            {"name": "Department Term Test Faculty", "code": "DTTF"}
        )
        self.department = self.Department.create(
            {
                "name": "Department Term Test Department",
                "code": "DTTD",
                "faculty_id": self.faculty.id,
            }
        )
        self.other_department = self.Department.create(
            {
                "name": "Department Term Test Other Department",
                "code": "DTTO",
                "faculty_id": self.faculty.id,
            }
        )
        self.inactive_department = self.Department.create(
            {
                "name": "Department Term Test Inactive Department",
                "code": "DTTI",
                "faculty_id": self.faculty.id,
                "active": False,
            }
        )

    def _term_values(self, **overrides):
        values = {
            "semester_id": self.semester.id,
            "department_id": self.department.id,
            "date_start": "2026-01-01",
            "date_end": "2026-06-30",
        }
        values.update(overrides)
        return values

    def test_related_academic_year_and_faculty_are_stored(self):
        term = self.DepartmentTerm.create(self._term_values())

        self.assertEqual(term.academic_year_id, self.academic_year)
        self.assertEqual(term.faculty_id, self.faculty)
        self.assertTrue(self.DepartmentTerm._fields["academic_year_id"].store)
        self.assertTrue(self.DepartmentTerm._fields["faculty_id"].store)
        self.assertTrue(self.DepartmentTerm._fields["state"].store)

    def test_department_is_unique_per_semester(self):
        self.DepartmentTerm.create(self._term_values())

        with self.assertRaises(IntegrityError):
            self.DepartmentTerm.create(self._term_values())

    def test_end_date_cannot_precede_start_date(self):
        with self.assertRaises(IntegrityError):
            self.DepartmentTerm.create(
                self._term_values(date_start="2026-03-02", date_end="2026-03-01")
            )

    def test_department_term_dates_must_fit_semester(self):
        with self.assertRaises(ValidationError):
            self.DepartmentTerm.create(
                self._term_values(date_start="2025-12-31", date_end="2026-06-30")
            )

        with self.assertRaises(ValidationError):
            self.DepartmentTerm.create(
                self._term_values(date_start="2026-01-01", date_end="2026-07-01")
            )

    def test_parents_cannot_exclude_existing_schedules(self):
        self.DepartmentTerm.create(self._term_values())

        with self.assertRaises(ValidationError):
            self.semester.write({"date_end": "2026-06-29"})

        with self.assertRaises(ValidationError):
            self.academic_year.write({"date_end": "2026-06-29"})

    def test_semester_must_fit_academic_year(self):
        with self.assertRaises(ValidationError):
            self.Semester.create(
                {
                    "name": "Department Term Outside Year",
                    "academic_year_id": self.academic_year.id,
                    "semester_type": "semester_2",
                    "date_start": "2026-07-01",
                    "date_end": "2027-01-01",
                }
            )

    def test_generate_department_terms_is_idempotent_and_preserves_overrides(self):
        custom_term = self.DepartmentTerm.create(
            self._term_values(date_start="2026-01-15", date_end="2026-06-15")
        )

        self.semester.action_generate_department_terms()
        terms = self.DepartmentTerm.search(
            [("semester_id", "=", self.semester.id)]
        )
        active_department_ids = set(
            self.Department.search([("active", "=", True)]).ids
        )
        self.assertEqual(set(terms.mapped("department_id").ids), active_department_ids)
        self.assertNotIn(self.inactive_department.id, terms.mapped("department_id").ids)
        self.assertEqual(custom_term.date_start, fields.Date.to_date("2026-01-15"))
        self.assertEqual(custom_term.date_end, fields.Date.to_date("2026-06-15"))

        self.semester.action_generate_department_terms()
        self.assertEqual(
            self.DepartmentTerm.search_count(
                [("semester_id", "=", self.semester.id)]
            ),
            len(active_department_ids),
        )
        custom_term.invalidate_recordset(["date_start", "date_end"])
        self.assertEqual(custom_term.date_start, fields.Date.to_date("2026-01-15"))
        self.assertEqual(custom_term.date_end, fields.Date.to_date("2026-06-15"))

    def test_cron_recomputes_stale_states(self):
        today = fields.Date.context_today(self.DepartmentTerm)
        state_year = self.AcademicYear.create(
            {
                "name": "Department Term State Academic Year",
                "date_start": today - timedelta(days=30),
                "date_end": today + timedelta(days=30),
            }
        )
        state_semester = self.Semester.create(
            {
                "name": "Department Term State Semester",
                "academic_year_id": state_year.id,
                "semester_type": "semester_1",
                "date_start": today - timedelta(days=20),
                "date_end": today + timedelta(days=20),
            }
        )
        state_department = self.Department.create(
            {
                "name": "Department Term State Department",
                "code": "DTTS",
                "faculty_id": self.faculty.id,
            }
        )
        ended_term = self.DepartmentTerm.create(
            {
                "semester_id": state_semester.id,
                "department_id": self.department.id,
                "date_start": today - timedelta(days=10),
                "date_end": today - timedelta(days=1),
            }
        )
        running_term = self.DepartmentTerm.create(
            {
                "semester_id": state_semester.id,
                "department_id": self.other_department.id,
                "date_start": today - timedelta(days=1),
                "date_end": today + timedelta(days=1),
            }
        )
        planned_term = self.DepartmentTerm.create(
            {
                "semester_id": state_semester.id,
                "department_id": state_department.id,
                "date_start": today + timedelta(days=1),
                "date_end": today + timedelta(days=5),
            }
        )
        terms = ended_term | running_term | planned_term
        terms.write({"state": "planned"})

        self.assertTrue(self.DepartmentTerm._cron_update_state())
        self.env.flush_all()
        terms.invalidate_recordset(["state"])
        self.assertEqual(ended_term.state, "ended")
        self.assertEqual(running_term.state, "running")
        self.assertEqual(planned_term.state, "planned")

    def test_academic_and_semester_counters(self):
        self.assertEqual(self.academic_year.semester_count, 1)
        self.Semester.create(
            {
                "name": "Department Term Counter Semester",
                "academic_year_id": self.academic_year.id,
                "semester_type": "semester_2",
                "date_start": "2026-07-01",
                "date_end": "2026-11-30",
            }
        )
        self.assertEqual(self.academic_year.semester_count, 2)

        subject = self.Subject.create(
            {
                "name": "Department Term Counter Subject",
                "code": "DTTC",
                "department_id": self.department.id,
            }
        )
        self.SemesterSubject.create(
            {"semester_id": self.semester.id, "subject_id": subject.id}
        )
        self.assertEqual(self.semester.subject_count, 1)

    def test_academic_year_name_and_current_are_unique(self):
        with self.assertRaises(IntegrityError):
            self.AcademicYear.create(
                {
                    "name": self.academic_year.name,
                    "date_start": "2027-01-01",
                    "date_end": "2027-12-31",
                }
            )
        self.AcademicYear.with_context(active_test=False).search(
            [("current", "=", True)]
        ).write({"current": False})
        self.env.flush_all()
        self.academic_year.write({"current": True})
        self.env.flush_all()
        with self.assertRaises(IntegrityError):
            self.AcademicYear.create(
                {
                    "name": "Department Term Second Current Year",
                    "date_start": "2027-01-01",
                    "date_end": "2027-12-31",
                    "current": True,
                }
            )

    def test_rollover_shifts_semesters_terms_and_holidays(self):
        self.academic_year.write({"state": "running"})
        term = self.DepartmentTerm.create(self._term_values(
            registration_start="2025-12-20",
            registration_end="2025-12-31",
            add_drop_start="2026-01-01",
            add_drop_end="2026-01-15",
            grade_deadline="2026-07-01",
        ))
        holiday = self.Holiday.create({
            "name": "Test Holiday",
            "date_start": "2026-02-02",
            "date_end": "2026-02-03",
            "academic_year_id": self.academic_year.id,
        })
        wizard = self.RolloverWizard.create({
            "source_year_id": self.academic_year.id,
            "new_year_name": "Department Term Rollover Year",
            "new_year_start_date": "2027-01-01",
        })
        wizard.action_rollover()
        new_year = self.AcademicYear.search(
            [("name", "=", "Department Term Rollover Year")], limit=1
        )
        new_term = self.DepartmentTerm.search([
            ("academic_year_id", "=", new_year.id),
            ("department_id", "=", self.department.id),
        ], limit=1)
        new_holiday = self.Holiday.search([
            ("academic_year_id", "=", new_year.id),
            ("name", "=", holiday.name),
        ], limit=1)
        self.assertEqual(new_year.state, "draft")
        self.assertEqual(new_term.date_start, term.date_start + timedelta(days=365))
        self.assertEqual(new_term.registration_end, term.registration_end + timedelta(days=365))
        self.assertEqual(new_holiday.date_start, holiday.date_start + timedelta(days=365))

    def test_closed_year_locks_children(self):
        term = self.DepartmentTerm.create(self._term_values())
        program = self.Program.create({
            "name": "Lock Test Program",
            "code": "LTP",
            "department_id": self.department.id,
        })
        student = self.Student.create({"name": "Lock Test Student"})
        enrollment = self.Enrollment.create({
            "student_id": student.id,
            "program_id": program.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "status": "enrolled",
        })
        category = self.env["university.assessment.category"].search([], limit=1)
        if not category:
            category = self.env["university.assessment.category"].create({
                "name": "Test Category", "code": "TC", "weight": 50
            })
        subject = self.Subject.create({
            "name": "Lock Test Subject",
            "code": "LTS",
            "department_id": self.department.id,
            "credits": 3,
        })
        grade_result = self.env["university.assessment.result"].create({
            "student_id": student.id,
            "subject_id": subject.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "category_id": category.id,
            "score": 85.0,
            "max_score": 100.0,
        })

        self.academic_year.write({"state": "closed"})
        with self.assertRaises(UserError):
            self.academic_year.write({"date_end": "2026-12-30"})
        with self.assertRaises(UserError):
            term.write({"date_end": "2026-06-29", "change_reason": "Correction"})
        with self.assertRaises(UserError):
            enrollment.write({"status": "completed"})
        with self.assertRaises(UserError):
            grade_result.write({"score": 90.0})

    def test_teaching_weeks_and_minimum_weeks_warning(self):
        term = self.DepartmentTerm.create(self._term_values())
        # teaching_weeks = (date_end - date_start) / 7 rounded to 1 decimal
        expected_weeks = round((term.date_end - term.date_start).days / 7.0, 1)
        self.assertEqual(term.teaching_weeks, expected_weeks)
        self.assertFalse(term.is_below_min_weeks)

        # Term with duration less than default 14 weeks
        short_term = self.DepartmentTerm.create(self._term_values(
            department_id=self.other_department.id,
            date_start="2026-01-01",
            date_end="2026-02-12",
        ))
        # 42 days / 7 = 6.0 weeks
        self.assertEqual(short_term.teaching_weeks, 6.0)
        self.assertTrue(short_term.is_below_min_weeks)

    def test_holiday_and_milestone_ranges_are_validated(self):
        with self.assertRaises(IntegrityError):
            self.Holiday.create({
                "name": "Invalid Holiday",
                "date_start": "2026-03-02",
                "date_end": "2026-03-01",
                "academic_year_id": self.academic_year.id,
            })
        with self.assertRaises(ValidationError):
            self.DepartmentTerm.create(self._term_values(
                registration_start="2026-02-02",
                registration_end="2026-02-01",
            ))

    def test_started_term_extension_requires_reason_and_posts_message(self):
        term = self.DepartmentTerm.create(self._term_values(date_end="2026-06-29"))
        with self.assertRaises(ValidationError):
            term.write({"date_end": "2026-06-30"})
        term.write({
            "date_end": "2026-06-30",
            "change_reason": "Additional examination day",
        })
        self.assertIn("Schedule changed by", term.message_ids[:1].body)

    def test_enrollment_requires_registration_window(self):
        today = fields.Date.context_today(self.DepartmentTerm)
        year = self.AcademicYear.create({
            "name": "Department Term Enrollment Year",
            "date_start": today - timedelta(days=30),
            "date_end": today + timedelta(days=90),
        })
        semester = self.Semester.create({
            "name": "Department Term Enrollment Semester",
            "academic_year_id": year.id,
            "semester_type": "semester_1",
            "date_start": today - timedelta(days=20),
            "date_end": today + timedelta(days=60),
        })
        term = self.DepartmentTerm.create({
            "semester_id": semester.id,
            "department_id": self.department.id,
            "date_start": today + timedelta(days=5),
            "date_end": today + timedelta(days=60),
            "registration_start": today + timedelta(days=1),
            "registration_end": today + timedelta(days=2),
            "add_drop_start": today + timedelta(days=5),
            "add_drop_end": today + timedelta(days=10),
        })
        program = self.Program.create({
            "name": "Department Term Enrollment Program",
            "code": "DTTEP",
            "department_id": self.department.id,
        })
        student = self.Student.create({"name": "Department Term Enrollment Student"})
        values = {
            "student_id": student.id,
            "program_id": program.id,
            "academic_year_id": year.id,
            "semester_id": semester.id,
            "status": "enrolled",
        }
        with self.assertRaises(ValidationError):
            self.Enrollment.create(values)
        term.write({
            "registration_start": today - timedelta(days=1),
            "registration_end": today + timedelta(days=1),
        })
        enrollment = self.Enrollment.create(values)
        self.assertEqual(enrollment.status, "enrolled")
