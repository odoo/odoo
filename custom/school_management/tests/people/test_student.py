from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestStudentModel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Faculty = cls.env["university.faculty"]
        cls.Department = cls.env["university.department"]
        cls.Program = cls.env["university.program"]
        cls.Student = cls.env["university.student"]

        cls.faculty_eng = cls.Faculty.create({
            "name": "Faculty of Engineering Test",
            "code": "FOE_T",
        })
        cls.faculty_biz = cls.Faculty.create({
            "name": "Faculty of Business Test",
            "code": "FOB_T",
        })

        cls.dept_cs = cls.Department.create({
            "name": "Department of CS Test",
            "code": "DCS_T",
            "faculty_id": cls.faculty_eng.id,
        })
        cls.dept_mkt = cls.Department.create({
            "name": "Department of Marketing Test",
            "code": "DMKT_T",
            "faculty_id": cls.faculty_biz.id,
        })

        cls.program_cs = cls.Program.create({
            "name": "Bachelor of CS Test",
            "code": "BCS_T",
            "department_id": cls.dept_cs.id,
        })
        cls.program_mkt = cls.Program.create({
            "name": "Bachelor of Marketing Test",
            "code": "BMKT_T",
            "department_id": cls.dept_mkt.id,
        })

    def test_faculty_follows_department_and_program(self):
        """Student faculty must match department faculty, and update when program changes."""
        student = self.Student.create({
            "name": "Alex Mercer",
            "program_id": self.program_cs.id,
        })
        self.assertEqual(student.department_id, self.dept_cs)
        self.assertEqual(student.faculty_id, self.faculty_eng)

        # Changing program updates department and faculty
        student.write({"program_id": self.program_mkt.id})
        self.assertEqual(student.department_id, self.dept_mkt)
        self.assertEqual(student.faculty_id, self.faculty_biz)

    def test_program_department_mismatch_rejected(self):
        """A student cannot be assigned a program that does not belong to the selected department."""
        with self.assertRaises(ValidationError):
            self.Student.create({
                "name": "Invalid Placement",
                "program_id": self.program_cs.id,
                "department_id": self.dept_mkt.id,
            })

    def test_duplicate_student_id_case_insensitive_rejected(self):
        """Student IDs must be unique regardless of letter case."""
        self.Student.create({
            "name": "First Student",
            "student_id": "STD-CASE-001",
        })

        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.Student.create({
                    "name": "Duplicate Lowercase",
                    "student_id": "std-case-001",
                })

    def test_sequence_generates_unique_student_id(self):
        """When student_id is omitted or blank, it is generated automatically via ir.sequence."""
        student1 = self.Student.create({"name": "Generated Student 1"})
        student2 = self.Student.create({"name": "Generated Student 2"})

        self.assertTrue(bool(student1.student_id))
        self.assertTrue(bool(student2.student_id))
        self.assertTrue(student1.student_id.startswith("STD-"))
        self.assertTrue(student2.student_id.startswith("STD-"))
        self.assertNotEqual(student1.student_id, student2.student_id)

    def test_kanban_and_list_fields_exist(self):
        """Check all required kanban and list fields exist with appropriate attributes."""
        student_model = self.Student
        fields_to_check = [
            "image_128",
            "image_1920",
            "name",
            "student_id",
            "program_id",
            "department_id",
            "faculty_id",
            "status",
        ]
        for field_name in fields_to_check:
            self.assertIn(field_name, student_model._fields, f"Field {field_name} must exist on university.student")

        image_128 = student_model._fields["image_128"]
        self.assertTrue(image_128.store, "image_128 must be stored for fast kanban loading")
        self.assertEqual(image_128.related, "image_1920", "image_128 must be related to image_1920")

        status_field = student_model._fields["status"]
        self.assertEqual(status_field.type, "selection")
        keys = [opt[0] for opt in status_field.selection]
        for expected in ["active", "suspended", "graduated", "dropped"]:
            self.assertIn(expected, keys, f"Status selection must contain '{expected}'")

    def test_cannot_delete_student_with_enrollment(self):
        """Students with active or historical enrollments must never be deleted."""
        student = self.Student.create({
            "name": "Enrolled Student Test",
            "program_id": self.program_cs.id,
        })
        academic_year = self.env["university.academic.year"].create({
            "name": "AY 2041 Test",
            "date_start": "2041-01-01",
            "date_end": "2041-12-31",
        })
        semester = self.env["university.semester"].create({
            "name": "Sem 1 Test",
            "academic_year_id": academic_year.id,
            "date_start": "2041-01-01",
            "date_end": "2041-06-30",
        })
        subject = self.env["university.subject"].create({
            "name": "Intro to CS Test",
            "code": "CS101T",
            "department_id": self.dept_cs.id,
        })
        section = self.env["university.class.section"].create({
            "name": "Section A",
            "subject_id": subject.id,
            "semester_id": semester.id,
        })
        self.env["university.enrollment"].create({
            "student_id": student.id,
            "class_section_id": section.id,
            "enrollment_date": "2026-01-15",
            "status": "enrolled",
        })

        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            student.unlink()

    def test_student_avatar_color_and_counts(self):
        """Verify avatar.mixin, color, and computed counts on student."""
        student = self.Student.create({
            "name": "Kesor Meas",
            "program_id": self.program_cs.id,
        })
        self.assertIn("avatar_128", self.Student._fields)
        self.assertIn("color", self.Student._fields)
        self.assertEqual(student.color, self.faculty_eng.color)
        self.assertEqual(student.enrollment_count, 0)
        self.assertEqual(student.submission_count, 0)
        self.assertEqual(student.report_card_count, 0)

        # Test stat button actions
        action_enrollments = student.action_view_enrollments()
        self.assertEqual(action_enrollments["res_model"], "university.enrollment")
        action_fees = student.action_view_fees()
        self.assertEqual(action_fees["res_model"], "university.fee")
        action_subs = student.action_view_submissions()
        self.assertEqual(action_subs["res_model"], "university.assignment.submission")
        action_rc = student.action_view_report_cards()
        self.assertEqual(action_rc["res_model"], "university.report.card")
