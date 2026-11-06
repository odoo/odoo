from datetime import timedelta
from uuid import uuid4

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSemesterSubject(TransactionCase):
    def setUp(self):
        super().setUp()
        self.AcademicYear = self.env["university.academic.year"]
        self.Semester = self.env["university.semester"]
        self.Subject = self.env["university.subject"]
        self.Offering = self.env["university.semester.subject"]

        code = uuid4().hex[:12]
        faculty = self.env["university.faculty"].create({
            "name": "Semester Subject Test Faculty %s" % code,
            "code": code,
        })
        self.department = self.env["university.department"].create({
            "name": "Semester Subject Test Department %s" % code,
            "code": code,
            "faculty_id": faculty.id,
        })
        self.open_year = self._create_year("Open", code, "running")
        self.closed_year = self._create_year("Closed", code, "closed")
        self.archived_year = self._create_year("Archived", code, "archived")
        self.open_semester = self._create_semester(self.open_year, "Open")
        self.closed_semester = self._create_semester(self.closed_year, "Closed")
        self.archived_semester = self._create_semester(self.archived_year, "Archived")

    def _create_year(self, label, code, state):
        return self.AcademicYear.create({
            "name": "Semester Subject %s Year %s" % (label, code),
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
            "state": state,
        })

    def _create_semester(self, year, label):
        model = self.Semester
        if year.state in ("closed", "archived"):
            model = model.with_context(allow_closed_year_write=True)
        return model.create({
            "name": "Semester Subject %s Semester" % label,
            "academic_year_id": year.id,
            "semester_type": "semester_1",
            "date_start": "2026-01-01",
            "date_end": "2026-06-30",
        })

    def _subject(self, label):
        return self.Subject.create({
            "name": "Semester Subject %s" % label,
            "code": uuid4().hex[:12],
            "department_id": self.department.id,
        })

    def _offering(self, semester, subject=None, maintenance=False, **values):
        model = self.Offering
        if maintenance:
            model = model.with_context(allow_closed_year_write=True)
        offering_values = {
            "semester_id": semester.id,
            "subject_id": (subject or self._subject("Offering")).id,
        }
        offering_values.update(values)
        return model.create(offering_values)

    def test_current_semester_is_searchable_and_unique_per_year(self):
        today = fields.Date.today()
        year = self.AcademicYear.create({
            "name": "Current Semester Test Year %s" % uuid4().hex,
            "date_start": today - timedelta(days=180),
            "date_end": today + timedelta(days=180),
            "active": False,
        })
        semester = self.Semester.create({
            "academic_year_id": year.id,
            "semester_type": "semester_1",
            "date_start": today - timedelta(days=56),
            "date_end": today + timedelta(days=56),
            "is_current": True,
        })

        current_semesters = self.Semester.search([
            ("academic_year_id", "=", year.id),
            ("is_current", "=", True),
        ])
        self.assertEqual(current_semesters, semester)
        self.assertTrue(semester.status)

    def test_create_in_open_year_preserves_derived_relationships(self):
        subject = self._subject("Open")
        offering = self._offering(self.open_semester, subject)

        self.assertEqual(offering.academic_year_id, self.open_year)
        self.assertEqual(offering.department_id, self.department)
        self.assertFalse("program_id" in self.Offering._fields)

    def test_create_in_closed_or_archived_year_is_blocked(self):
        for semester in (self.closed_semester, self.archived_semester):
            with self.assertRaises(UserError):
                self._offering(semester)

    def test_create_uses_default_semester_from_context(self):
        with self.assertRaises(UserError):
            self.Offering.with_context(
                default_semester_id=self.closed_semester.id
            ).create({"subject_id": self._subject("Default Closed").id})

    def test_offerings_cannot_move_into_or_out_of_locked_years(self):
        open_offering = self._offering(self.open_semester)
        with self.assertRaises(UserError):
            open_offering.write({"semester_id": self.closed_semester.id})

        locked_offering = self._offering(self.closed_semester, maintenance=True)
        with self.assertRaises(UserError):
            locked_offering.write({"semester_id": self.open_semester.id})

    def test_locked_offerings_cannot_be_edited_archived_unarchived_or_deleted(self):
        offering = self._offering(self.closed_semester, maintenance=True)
        with self.assertRaises(UserError):
            offering.write({"active": False})
        offering.with_context(allow_closed_year_write=True).write({"active": False})

        archived_offering = offering.with_context(active_test=False)
        with self.assertRaises(UserError):
            archived_offering.write({"active": True})
        with self.assertRaises(UserError):
            archived_offering.unlink()

    def test_unique_constraint_rejects_active_and_archived_duplicates(self):
        subject = self._subject("Duplicate")
        self._offering(self.open_semester, subject)
        with self.cr.savepoint(), self.assertRaises(IntegrityError):
            self._offering(self.open_semester, subject)

        offering = self.Offering.search([
            ("semester_id", "=", self.open_semester.id),
            ("subject_id", "=", subject.id),
        ])
        offering.write({"active": False})
        with self.cr.savepoint(), self.assertRaises(IntegrityError):
            self._offering(self.open_semester, subject)

    def test_unique_constraint_rejects_duplicate_pairs_in_one_batch(self):
        subject = self._subject("Batch Duplicate")
        values = {
            "semester_id": self.open_semester.id,
            "subject_id": subject.id,
        }
        with self.cr.savepoint(), self.assertRaises(IntegrityError):
            self.Offering.create([values, dict(values)])

    def test_client_context_flag_does_not_authorize_closed_year_maintenance(self):
        login = "semester-subject-%s@example.test" % uuid4().hex
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Unprivileged Semester Subject User",
            "login": login,
            "email": login,
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        with self.assertRaises(UserError):
            self.Offering.with_user(user).with_context(
                allow_closed_year_write=True
            ).create({
                "semester_id": self.closed_semester.id,
                "subject_id": self._subject("Unauthorized Maintenance").id,
            })

    def test_privileged_maintenance_context_remains_available(self):
        offering = self._offering(self.closed_semester, maintenance=True)
        offering.with_context(allow_closed_year_write=True).write({"active": False})
        self.assertFalse(offering.active)

    def test_semester_cannot_move_offerings_into_locked_year(self):
        self._offering(self.open_semester)
        with self.assertRaises(UserError):
            self.open_semester.write({"academic_year_id": self.closed_year.id})

    def test_subject_cannot_cascade_delete_locked_offerings(self):
        subject = self._subject("Locked Subject")
        self._offering(self.closed_semester, subject, maintenance=True)
        with self.assertRaises(UserError):
            subject.unlink()
