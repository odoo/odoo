from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestEnrollment(TransactionCase):
    def setUp(self):
        super().setUp()
        Faculty = self.env["university.faculty"]
        Department = self.env["university.department"]
        Program = self.env["university.program"]
        Year = self.env["university.academic.year"]
        Semester = self.env["university.semester"]
        self.Student = self.env["university.student"]
        self.Enrollment = self.env["university.enrollment"]
        self.StudentWizard = self.env["university.student.enrollment.wizard"]
        self.Wizard = self.env["university.bulk.enrollment.wizard"]
        Section = self.env["university.class.section"]

        self.faculty = Faculty.create({"name": "Test Science", "code": "TESTSCI"})
        self.department = Department.create(
            {
                "name": "Test Physics",
                "code": "TESTPHY",
                "faculty_id": self.faculty.id,
            }
        )
        self.program = Program.create(
            {
                "name": "Test BSc Physics",
                "code": "TEST-BSC-PHY",
                "department_id": self.department.id,
            }
        )
        self.year = Year.create(
            {
                "name": "Enrollment Test Year 2036-2037",
                "date_start": "2036-09-01",
                "date_end": "2037-06-30",
            }
        )
        self.semester = Semester.create(
            {
                "name": "Semester 1",
                "academic_year_id": self.year.id,
                "semester_type": "semester_1",
                "date_start": "2036-09-01",
                "date_end": "2036-12-22",
            }
        )
        self.section = Section.create(
            {
                "name": "GM-Y1-A",
                "program_id": self.program.id,
                "semester_id": self.semester.id,
                "capacity": 2,
            }
        )

    def _make_student(self, **kw):
        vals = {"name": "Student", "status": "active"}
        vals.update(kw)
        return self.Student.create(vals)

    def test_single_major_enrollment(self):
        student = self._make_student(program_id=self.program.id)
        enrollment = self.Enrollment.create(
            {
                "student_id": student.id,
                "program_id": self.program.id,
                "section_id": self.section.id,
                "academic_year_id": self.year.id,
                "semester_id": self.semester.id,
            }
        )
        self.assertEqual(enrollment.department_id, self.department)
        self.assertEqual(enrollment.faculty_id, self.faculty)
        self.assertEqual(enrollment.status, "draft")
        enrollment.action_confirm()
        self.assertEqual(enrollment.status, "enrolled")

    def test_student_wizard_enrolls_without_class_section(self):
        student = self._make_student(
            program_id=self.program.id,
            academic_year_id=self.year.id,
            current_semester_id=self.semester.id,
        )
        wizard = self.StudentWizard.create({
            "student_id": student.id,
            "program_id": self.program.id,
            "academic_year_id": self.year.id,
            "semester_id": self.semester.id,
        })

        wizard.action_register_enrollments()

        enrollment = self.Enrollment.search([
            ("student_id", "=", student.id),
            ("program_id", "=", self.program.id),
            ("academic_year_id", "=", self.year.id),
            ("semester_id", "=", self.semester.id),
            ("section_id", "=", False),
        ])
        self.assertEqual(len(enrollment), 1)
        self.assertEqual(enrollment.status, "enrolled")

    def test_student_wizard_defaults_academic_data_from_student(self):
        student = self._make_student(
            program_id=self.program.id,
            academic_year_id=self.year.id,
            current_semester_id=self.semester.id,
        )
        defaults = self.StudentWizard.with_context(
            default_student_id=student.id
        ).default_get([
            "student_id",
            "program_id",
            "academic_year_id",
            "semester_id",
        ])

        self.assertEqual(defaults["student_id"], student.id)
        self.assertEqual(defaults["program_id"], self.program.id)
        self.assertEqual(defaults["academic_year_id"], self.year.id)
        self.assertEqual(defaults["semester_id"], self.semester.id)

    def test_student_wizard_can_still_assign_selected_class(self):
        student = self._make_student(
            program_id=self.program.id,
            academic_year_id=self.year.id,
            current_semester_id=self.semester.id,
        )
        wizard = self.StudentWizard.create({
            "student_id": student.id,
            "program_id": self.program.id,
            "academic_year_id": self.year.id,
            "semester_id": self.semester.id,
            "section_ids": [(6, 0, [self.section.id])],
        })

        wizard.action_register_enrollments()

        enrollment = self.Enrollment.search([
            ("student_id", "=", student.id),
            ("section_id", "=", self.section.id),
        ])
        self.assertEqual(len(enrollment), 1)
        self.assertEqual(enrollment.program_id, self.program)

    def test_bulk_enroll_students(self):
        s1 = self._make_student(program_id=self.program.id)
        s2 = self._make_student(program_id=self.program.id)
        wizard = self.Wizard.create(
            {
                "faculty_id": self.faculty.id,
                "department_id": self.department.id,
                "program_id": self.program.id,
                "academic_year_id": self.year.id,
                "semester_id": self.semester.id,
                "section_id": self.section.id,
                "student_ids": [(6, 0, [s1.id, s2.id])],
            }
        )
        wizard.action_enroll_students()
        self.assertEqual(
            self.Enrollment.search_count(
                [
                    ("student_id", "in", [s1.id, s2.id]),
                    ("program_id", "=", self.program.id),
                ]
            ),
            2,
        )


class TestEnrollmentModelRules(TransactionCase):
    def setUp(self):
        super().setUp()
        self.faculty = self.env["university.faculty"].create({
            "name": "Engineering Faculty",
            "code": "EFAC",
        })
        self.department = self.env["university.department"].create({
            "name": "Software Engineering",
            "code": "SOFTE",
            "faculty_id": self.faculty.id,
        })
        self.program = self.env["university.program"].create({
            "name": "BSc Software Engineering",
            "code": "BS-SE",
            "department_id": self.department.id,
        })
        self.subject = self.env["university.subject"].create({
            "name": "Data Structures",
            "code": "CS201",
            "department_id": self.department.id,
            "program_ids": [(6, 0, [self.program.id])],
        })
        self.teacher = self.env["university.teacher"].create({
            "name": "Dr. Alan Turing",
            "department_id": self.department.id,
        })
        self.year = self.env["university.academic.year"].create({
            "name": "Rules Test Academic Year 2038",
            "date_start": "2038-01-01",
            "date_end": "2038-12-31",
            "state": "open",
        })
        self.semester = self.env["university.semester"].create({
            "name": "Spring 2038",
            "academic_year_id": self.year.id,
            "semester_type": "semester_1",
            "date_start": "2038-01-01",
            "date_end": "2038-06-30",
        })
        self.section = self.env["university.class.section"].create({
            "name": "SE-2026-A",
            "program_id": self.program.id,
            "subject_id": self.subject.id,
            "teacher_id": self.teacher.id,
            "semester_id": self.semester.id,
            "capacity": 2,
            "active": True,
        })
        self.student = self.env["university.student"].create({
            "name": "Alice Wonderland",
            "program_id": self.program.id,
            "status": "active",
            "active": True,
        })

    def test_derived_fields_follow_class_section(self):
        """User only chooses student and class section. All academic fields derive automatically."""
        enrollment = self.env["university.enrollment"].create({
            "student_id": self.student.id,
            "class_section_id": self.section.id,
        })
        self.assertEqual(enrollment.program_id, self.program)
        self.assertEqual(enrollment.department_id, self.department)
        self.assertEqual(enrollment.faculty_id, self.faculty)
        self.assertEqual(enrollment.subject_id, self.subject)
        self.assertEqual(enrollment.instructor_id, self.teacher)
        self.assertEqual(enrollment.semester_id, self.semester)
        self.assertEqual(enrollment.academic_year_id, self.year)
        self.assertEqual(enrollment.status, "draft")
        self.assertEqual(enrollment.enrollment_date, fields.Date.today())

    def test_unique_student_section(self):
        """A student cannot be enrolled twice in the same class section."""
        self.env["university.enrollment"].create({
            "student_id": self.student.id,
            "class_section_id": self.section.id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env["university.enrollment"].create({
                    "student_id": self.student.id,
                    "class_section_id": self.section.id,
                })

    def test_inactive_student_rejected(self):
        """An inactive student cannot be enrolled."""
        inactive_student = self.env["university.student"].create({
            "name": "Bob Sleepy",
            "active": False,
        })
        with self.assertRaises(ValidationError):
            self.env["university.enrollment"].create({
                "student_id": inactive_student.id,
                "class_section_id": self.section.id,
            })

    def test_closed_section_rejected(self):
        """An inactive / closed class section cannot accept enrollments."""
        self.section.active = False
        with self.assertRaises(ValidationError):
            self.env["university.enrollment"].create({
                "student_id": self.student.id,
                "class_section_id": self.section.id,
            })

    def test_registration_window(self):
        """Enrollment must respect the department term registration window."""
        today = fields.Date.today()
        future_year = self.env["university.academic.year"].search([
            ("date_start", "<=", today),
            ("date_end", ">=", today),
        ], limit=1)
        if not future_year:
            future_year = self.env["university.academic.year"].create({
                "name": "Registration Window Year",
                "date_start": today - timedelta(days=30),
                "date_end": today + timedelta(days=300),
                "state": "open",
            })
        future_sem = self.env["university.semester"].search([
            ("academic_year_id", "=", future_year.id),
            ("semester_type", "=", "semester_2"),
        ], limit=1)
        if not future_sem:
            future_sem = self.env["university.semester"].create({
                "name": "Registration Window Semester",
                "academic_year_id": future_year.id,
                "semester_type": "semester_2",
                "date_start": today + timedelta(days=20),
                "date_end": today + timedelta(days=120),
            })
        future_section = self.env["university.class.section"].create({
            "name": "SE-Future-A",
            "program_id": self.program.id,
            "subject_id": self.subject.id,
            "semester_id": future_sem.id,
            "active": True,
        })
        # Create department term with window in the future
        term = self.env["university.department.term"].search([
            ("semester_id", "=", future_sem.id),
            ("department_id", "=", self.department.id),
        ], limit=1)
        if not term:
            term = self.env["university.department.term"].create({
                "semester_id": future_sem.id,
                "department_id": self.department.id,
                "date_start": future_sem.date_start,
                "date_end": future_sem.date_end,
                "registration_start": today + timedelta(days=5),
                "registration_end": today + timedelta(days=15),
            })
        else:
            term.write({
                "registration_start": today + timedelta(days=5),
                "registration_end": today + timedelta(days=15),
            })
        with self.assertRaises(ValidationError):
            self.env["university.enrollment"].create({
                "student_id": self.student.id,
                "class_section_id": future_section.id,
            })

        # Update term window to include today
        term.write({
            "registration_start": today - timedelta(days=2),
            "registration_end": today + timedelta(days=15),
        })
        enrollment = self.env["university.enrollment"].create({
            "student_id": self.student.id,
            "class_section_id": future_section.id,
        })
        self.assertTrue(enrollment)

    def test_capacity(self):
        """Section capacity cannot be exceeded by confirmed enrollments."""
        self.section.capacity = 1
        student2 = self.env["university.student"].create({
            "name": "Charlie Student",
            "status": "active",
            "active": True,
        })
        e1 = self.env["university.enrollment"].create({
            "student_id": self.student.id,
            "class_section_id": self.section.id,
        })
        e1.action_confirm()

        e2 = self.env["university.enrollment"].create({
            "student_id": student2.id,
            "class_section_id": self.section.id,
        })
        with self.assertRaises(ValidationError):
            e2.action_confirm()

    def test_closed_year_lock(self):
        """Closed and archived academic years block create, write, and unlink."""
        enrollment = self.env["university.enrollment"].create({
            "student_id": self.student.id,
            "class_section_id": self.section.id,
        })
        self.year.state = "closed"

        with self.assertRaises(UserError):
            enrollment.write({"enrollment_date": fields.Date.today()})

        with self.assertRaises(UserError):
            enrollment.unlink()

        student2 = self.env["university.student"].create({
            "name": "Dana Closed",
            "status": "active",
            "active": True,
        })
        with self.assertRaises(UserError):
            self.env["university.enrollment"].create({
                "student_id": student2.id,
                "class_section_id": self.section.id,
            })

    def test_status_transitions(self):
        """Status workflow draft -> enrolled -> completed, drop and reset to draft."""
        enrollment = self.env["university.enrollment"].create({
            "student_id": self.student.id,
            "class_section_id": self.section.id,
        })
        self.assertEqual(enrollment.status, "draft")

        # Draft -> Enrolled
        enrollment.action_confirm()
        self.assertEqual(enrollment.status, "enrolled")

        # Invalid transition: confirm when already enrolled
        with self.assertRaises(UserError):
            enrollment.action_confirm()

        # Enrolled -> Completed
        enrollment.action_complete()
        self.assertEqual(enrollment.status, "completed")

        # Completed is final: cannot drop or complete again
        with self.assertRaises(UserError):
            enrollment.action_drop()

        # Test Drop and Reset to Draft on a new enrollment
        student2 = self.env["university.student"].create({
            "name": "Eve Dropper",
            "status": "active",
            "active": True,
        })
        section2 = self.env["university.class.section"].create({
            "name": "SE-2026-B",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
            "capacity": 10,
        })
        e2 = self.env["university.enrollment"].create({
            "student_id": student2.id,
            "class_section_id": section2.id,
        })
        e2.action_drop()
        self.assertEqual(e2.status, "dropped")

        e2.action_reset_draft()
        self.assertEqual(e2.status, "draft")

    def test_duplicate_subject_same_semester(self):
        """A student cannot be enrolled in the same subject twice in the same semester."""
        section_b = self.env["university.class.section"].create({
            "name": "SE-2026-SubjectDup",
            "program_id": self.program.id,
            "subject_id": self.subject.id,
            "semester_id": self.semester.id,
            "capacity": 10,
        })
        self.env["university.enrollment"].create({
            "student_id": self.student.id,
            "class_section_id": self.section.id,
        })
        with self.assertRaises(ValidationError):
            self.env["university.enrollment"].create({
                "student_id": self.student.id,
                "class_section_id": section_b.id,
            })
