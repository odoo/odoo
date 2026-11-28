from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestTimetableAttendanceFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.year = cls.env["university.academic.year"].create({
            "name": "Flow Test Year",
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
        })
        cls.semester = cls.env["university.semester"].create({
            "name": "Flow Test Semester",
            "academic_year_id": cls.year.id,
            "semester_type": "semester_1",
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
        })
        cls.faculty = cls.env["university.faculty"].create({
            "name": "Flow Faculty",
            "code": "FL-FAC",
        })
        cls.department = cls.env["university.department"].create({
            "name": "Flow Department",
            "code": "FL-DEP",
            "faculty_id": cls.faculty.id,
        })
        cls.dean_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Flow Dean",
            "login": "flow-dean",
            "group_ids": [Command.set([cls.env.ref("school_management.group_school_dean").id])],
        })
        cls.dean_staff = cls.env["university.teacher"].create({
            "name": "Flow Dean Staff",
            "user_id": cls.dean_user.id,
            "department_id": cls.department.id,
        })
        cls.env["university.academic.assignment"].create({
            "role": "dean",
            "faculty_id": cls.faculty.id,
            "staff_id": cls.dean_staff.id,
            "start_date": "2026-01-01",
            "active": True,
        })
        cls.hod_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Flow HOD",
            "login": "flow-hod",
            "group_ids": [Command.set([cls.env.ref("school_management.group_school_hod").id])],
        })
        cls.hod_staff = cls.env["university.teacher"].create({
            "name": "Flow HOD Staff",
            "user_id": cls.hod_user.id,
            "department_id": cls.department.id,
        })
        cls.env["university.academic.assignment"].create({
            "role": "department_head",
            "department_id": cls.department.id,
            "staff_id": cls.hod_staff.id,
            "start_date": "2026-01-01",
            "active": True,
        })
        cls.program = cls.env["university.program"].create({
            "name": "Flow Program",
            "code": "FL-PRG",
            "department_id": cls.department.id,
        })
        cls.teacher_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Flow Assigned Teacher",
            "login": "flow-assigned-teacher",
            "group_ids": [Command.set([cls.env.ref("school_management.group_school_teacher").id])],
        })
        cls.teacher = cls.env["university.teacher"].create({
            "name": "Flow Assigned Teacher",
            "user_id": cls.teacher_user.id,
            "department_id": cls.department.id,
        })
        cls.other_teacher_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Flow Other Teacher",
            "login": "flow-other-teacher",
            "group_ids": [Command.set([cls.env.ref("school_management.group_school_teacher").id])],
        })
        cls.student_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Flow Student User",
            "login": "flow-student-user",
            "group_ids": [Command.set([cls.env.ref("school_management.group_school_student").id])],
        })
        cls.admin_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Flow Admin User",
            "login": "flow-admin-user",
            "group_ids": [Command.set([cls.env.ref("school_management.group_school_admin").id])],
        })
        cls.subject = cls.env["university.subject"].create({
            "name": "Flow Subject",
            "code": "FL-SUB",
            "department_id": cls.department.id,
        })
        cls.section = cls.env["university.class.section"].create({
            "name": "FL-SEC-101",
            "program_id": cls.program.id,
            "semester_id": cls.semester.id,
            "teacher_id": cls.teacher.id,
            "subject_id": cls.subject.id,
        })
        cls.slot = cls.env["university.timetable.slot"].create({
            "section_id": cls.section.id,
            "subject_id": cls.subject.id,
            "teacher_id": cls.teacher.id,
            "start_time": fields.Datetime.to_datetime("2026-10-10 09:00:00"),
            "end_time": fields.Datetime.to_datetime("2026-10-10 10:30:00"),
        })

    def test_assigned_teacher_can_manage_attendance_and_open_sheet(self):
        slot_as_teacher = self.slot.with_user(self.teacher_user)
        self.assertTrue(slot_as_teacher.check_can_manage_attendance())
        action = slot_as_teacher.action_track_attendance()
        self.assertEqual(action.get("type"), "ir.actions.client")
        self.assertEqual(action.get("tag"), "university_attendance_sheet")
        self.assertEqual(action.get("context", {}).get("default_section_id"), self.section.id)

    def test_admin_can_manage_attendance_and_open_sheet(self):
        slot_as_admin = self.slot.with_user(self.admin_user)
        self.assertTrue(slot_as_admin.check_can_manage_attendance())
        action = slot_as_admin.action_track_attendance()
        self.assertEqual(action.get("tag"), "university_attendance_sheet")

    def test_hod_and_dean_can_manage_attendance(self):
        self.assertTrue(self.slot.with_user(self.hod_user).check_can_manage_attendance())
        self.assertTrue(self.slot.with_user(self.dean_user).check_can_manage_attendance())

    def test_student_cannot_manage_attendance_and_gets_access_error(self):
        slot_as_student = self.slot.with_user(self.student_user)
        self.assertFalse(slot_as_student.check_can_manage_attendance())
        with self.assertRaises(AccessError):
            slot_as_student.action_track_attendance()

    def test_unassigned_teacher_cannot_manage_attendance_and_gets_access_error(self):
        slot_as_other = self.slot.with_user(self.other_teacher_user)
        self.assertFalse(slot_as_other.check_can_manage_attendance())
        with self.assertRaises(AccessError):
            slot_as_other.action_track_attendance()
