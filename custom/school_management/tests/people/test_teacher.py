from datetime import datetime
from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestTeacherModel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Faculty = cls.env["university.faculty"]
        cls.Department = cls.env["university.department"]
        cls.Program = cls.env["university.program"]
        cls.Subject = cls.env["university.subject"]
        cls.AcademicYear = cls.env["university.academic.year"]
        cls.Semester = cls.env["university.semester"]
        cls.ClassSection = cls.env["university.class.section"]
        cls.TimetableSlot = cls.env["university.timetable.slot"]
        cls.Teacher = cls.env["university.teacher"]
        cls.Attendance = cls.env["university.staff.attendance"]
        cls.Assignment = cls.env["university.academic.assignment"]

        cls.faculty_eng = cls.Faculty.create({
            "name": "Faculty of Engineering Teacher Test",
            "code": "FOE_TT",
            "color": 4,
        })
        cls.dept_cs = cls.Department.create({
            "name": "Department of CS Teacher Test",
            "code": "DCS_TT",
            "faculty_id": cls.faculty_eng.id,
        })
        cls.program_cs = cls.Program.create({
            "name": "Bachelor of CS Teacher Test",
            "code": "BCS_TT",
            "department_id": cls.dept_cs.id,
        })
        cls.subject_cs101 = cls.Subject.create({
            "name": "Intro to CS Test",
            "code": "CS101_TT",
            "department_id": cls.dept_cs.id,
            "program_ids": [(6, 0, [cls.program_cs.id])],
        })
        cls.academic_year = cls.AcademicYear.create({
            "name": "Academic Year 2026 Teacher Test",
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
        })
        cls.semester = cls.Semester.create({
            "name": "Semester 1 Teacher Test",
            "academic_year_id": cls.academic_year.id,
            "semester_type": "semester_1",
            "date_start": "2026-01-01",
            "date_end": "2026-06-30",
        })

    def test_title_split_and_display_name(self):
        """Embedded titles must be extracted into title field and display_name computed."""
        t1 = self.Teacher.create({"name": "Dr. John Doe"})
        self.assertEqual(t1.title, "dr")
        self.assertEqual(t1.name, "John Doe")
        self.assertEqual(t1.display_name, "Dr. John Doe")

        t2 = self.Teacher.create({"name": "Prof. Charles Xavier"})
        self.assertEqual(t2.title, "prof")
        self.assertEqual(t2.name, "Charles Xavier")
        self.assertEqual(t2.display_name, "Prof. Charles Xavier")

        t3 = self.Teacher.create({"name": "Reaksa", "title": "mr"})
        self.assertEqual(t3.title, "mr")
        self.assertEqual(t3.name, "Reaksa")
        self.assertEqual(t3.display_name, "Mr. Reaksa")

        t4 = self.Teacher.create({"name": "Plain Teacher"})
        self.assertFalse(t4.title)
        self.assertEqual(t4.name, "Plain Teacher")
        self.assertEqual(t4.display_name, "Plain Teacher")

    def test_name_normalization(self):
        """Lowercase names must be capitalized and leading whitespace stripped."""
        t1 = self.Teacher.create({"name": "meng lay"})
        self.assertEqual(t1.name, "Meng Lay")

        t2 = self.Teacher.create({"name": "  dr.   sarah   jenkins  "})
        self.assertEqual(t2.title, "dr")
        self.assertEqual(t2.name, "Sarah Jenkins")
        self.assertEqual(t2.display_name, "Dr. Sarah Jenkins")

        # Test write update
        t1.write({"name": "ms. sarah connor"})
        self.assertEqual(t1.title, "ms")
        self.assertEqual(t1.name, "Sarah Connor")
        self.assertEqual(t1.display_name, "Ms. Sarah Connor")

    def test_sequence_generates_unique_teacher_id(self):
        """Blank teacher_id is populated from ir.sequence with TCH- prefix."""
        t1 = self.Teacher.create({"name": "Sequence Teacher 1"})
        t2 = self.Teacher.create({"name": "Sequence Teacher 2"})

        self.assertTrue(bool(t1.teacher_id))
        self.assertTrue(bool(t2.teacher_id))
        self.assertTrue(t1.teacher_id.startswith("TCH-"))
        self.assertTrue(t2.teacher_id.startswith("TCH-"))
        self.assertNotEqual(t1.teacher_id, t2.teacher_id)

    def test_teacher_id_case_insensitive_unique(self):
        """Staff IDs must be unique regardless of case."""
        self.Teacher.create({
            "name": "Teacher Alpha",
            "teacher_id": "TCH-CASE-001",
        })

        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.Teacher.create({
                    "name": "Teacher Beta",
                    "teacher_id": "tch-case-001",
                })

    def test_email_validation_and_case_insensitive_unique(self):
        """Email must follow valid format and be unique case-insensitively."""
        with self.assertRaises(ValidationError):
            self.Teacher.create({
                "name": "Invalid Email Staff",
                "email": "invalid-email-format",
            })

        t1 = self.Teacher.create({
            "name": "Email Staff 1",
            "email": "teacher1@example.com",
        })
        self.assertEqual(t1.email, "teacher1@example.com")

        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.Teacher.create({
                    "name": "Duplicate Email Staff",
                    "email": "TEACHER1@EXAMPLE.COM",
                })

    def test_is_head_computation(self):
        """is_head must compute to True when teacher has an active leadership assignment."""
        teacher = self.Teacher.create({
            "name": "Dean Candidate",
            "department_id": self.dept_cs.id,
        })
        self.assertFalse(teacher.is_head)

        assignment = self.Assignment.create({
            "staff_id": teacher.id,
            "role": "department_head",
            "department_id": self.dept_cs.id,
            "start_date": fields.Date.today(),
            "active": True,
        })
        teacher._compute_is_head()
        self.assertTrue(teacher.is_head)

        assignment.write({"active": False})
        teacher._compute_is_head()
        self.assertFalse(teacher.is_head)

    def test_presence_and_leave_computation_and_search(self):
        """is_present and on_leave compute from staff attendance and support search domains."""
        today = fields.Date.today()
        teacher_present = self.Teacher.create({"name": "Present Teacher"})
        teacher_leave = self.Teacher.create({"name": "On Leave Teacher"})
        teacher_none = self.Teacher.create({"name": "No Record Teacher"})

        self.Attendance.create({
            "staff_id": teacher_present.id,
            "date": today,
            "status": "present",
        })
        self.Attendance.create({
            "staff_id": teacher_leave.id,
            "date": today,
            "status": "leave",
        })

        teachers = teacher_present | teacher_leave | teacher_none
        teachers._compute_presence()

        self.assertTrue(teacher_present.is_present)
        self.assertFalse(teacher_present.on_leave)

        self.assertFalse(teacher_leave.is_present)
        self.assertTrue(teacher_leave.on_leave)

        self.assertFalse(teacher_none.is_present)
        self.assertFalse(teacher_none.on_leave)

        # Test search domains
        present_results = self.Teacher.search([("id", "in", teachers.ids), ("is_present", "=", True)])
        self.assertIn(teacher_present, present_results)
        self.assertNotIn(teacher_leave, present_results)

        leave_results = self.Teacher.search([("id", "in", teachers.ids), ("on_leave", "=", True)])
        self.assertIn(teacher_leave, leave_results)
        self.assertNotIn(teacher_present, leave_results)

    def test_teaching_stats_computation(self):
        """class_count and weekly_hours compute from section_ids and timetable_slot_ids."""
        teacher = self.Teacher.create({"name": "Teaching Staff"})

        section = self.ClassSection.create({
            "name": "CS101-SecA",
            "semester_id": self.semester.id,
            "subject_id": self.subject_cs101.id,
            "teacher_id": teacher.id,
        })

        now = datetime.now()
        start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        end = now.replace(hour=11, minute=0, second=0, microsecond=0)

        slot = self.TimetableSlot.create({
            "teacher_id": teacher.id,
            "section_id": section.id,
            "subject_id": self.subject_cs101.id,
            "start_time": start,
            "end_time": end,
        })

        teacher._compute_teaching_stats()
        self.assertEqual(teacher.class_count, 1)
        self.assertEqual(teacher.weekly_hours, 2.0)

    def test_unlink_safeguard(self):
        """Deleting a teacher with linked classes or attendance records must raise UserError."""
        teacher_busy = self.Teacher.create({"name": "Busy Teacher"})
        self.Attendance.create({
            "staff_id": teacher_busy.id,
            "date": fields.Date.today(),
            "status": "present",
        })

        with self.assertRaises(UserError):
            teacher_busy.unlink()

        teacher_free = self.Teacher.create({"name": "Free Teacher"})
        # Should unlink cleanly
        teacher_free.unlink()
        self.assertFalse(teacher_free.exists())

    def test_avatar_mixin_and_faculty_color(self):
        """avatar_128 must exist and faculty color must be inherited."""
        teacher = self.Teacher.create({
            "name": "Color Test Teacher",
            "department_id": self.dept_cs.id,
        })
        self.assertTrue(hasattr(teacher, "avatar_128"))
        self.assertEqual(teacher.color, self.faculty_eng.color)
