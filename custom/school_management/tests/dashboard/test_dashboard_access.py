from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDashboardAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_user = cls.env.ref("base.group_user")
        cls.group_student = cls.env.ref("school_management.group_school_student")
        cls.group_teacher = cls.env.ref("school_management.group_school_teacher")
        cls.group_hod = cls.env.ref("school_management.group_school_hod")
        cls.group_admin = cls.env.ref("school_management.group_school_admin")

        cls.year = cls.env["university.academic.year"].create({
            "name": "Dashboard Access Test Year",
            "date_start": "2026-09-01",
            "date_end": "2027-06-30",
        })
        cls.semester = cls.env["university.semester"].create({
            "name": "Dashboard Access Test Semester",
            "academic_year_id": cls.year.id,
            "semester_type": "semester_1",
            "date_start": cls.year.date_start,
            "date_end": "2027-01-31",
        })
        cls.faculty = cls.env["university.faculty"].create({
            "name": "Dashboard Access Faculty",
            "code": "DASH-ACCESS-FAC",
        })
        cls.other_faculty = cls.env["university.faculty"].create({
            "name": "Dashboard Access Other Faculty",
            "code": "DASH-ACCESS-OTHER-FAC",
        })
        cls.department = cls.env["university.department"].create({
            "name": "Dashboard Access Department",
            "code": "DASH-ACCESS-DEPT",
            "faculty_id": cls.faculty.id,
        })
        cls.other_department = cls.env["university.department"].create({
            "name": "Dashboard Access Other Department",
            "code": "DASH-ACCESS-OTHER-DEPT",
            "faculty_id": cls.other_faculty.id,
        })
        cls.program = cls.env["university.program"].create({
            "name": "Dashboard Access Program",
            "code": "DASH-ACCESS-PROG",
            "department_id": cls.department.id,
        })
        cls.other_program = cls.env["university.program"].create({
            "name": "Dashboard Access Other Program",
            "code": "DASH-ACCESS-OTHER-PROG",
            "department_id": cls.other_department.id,
        })

        cls.user_teacher = cls._create_user("dashboard.access.teacher", cls.group_teacher)
        cls.teacher = cls._create_teacher(
            "Dashboard Access Teacher", cls.user_teacher, cls.department, "DASH-ACCESS-T1",
        )
        cls.user_other_teacher = cls._create_user(
            "dashboard.access.other.teacher", cls.group_teacher,
        )
        cls.other_teacher = cls._create_teacher(
            "Dashboard Access Other Teacher", cls.user_other_teacher,
            cls.other_department, "DASH-ACCESS-T2",
        )

        cls.user_hod = cls._create_user("dashboard.access.hod", cls.group_hod)
        cls.hod = cls._create_teacher(
            "Dashboard Access HOD", cls.user_hod, cls.department, "DASH-ACCESS-HOD",
        )
        cls.env["university.academic.assignment"].create({
            "staff_id": cls.hod.id,
            "department_id": cls.department.id,
            "role": "department_head",
            "active": True,
            "start_date": "2026-01-01",
        })
        cls.hod._compute_managed_scopes()
        cls.department._compute_head_id()

        cls.section = cls.env["university.class.section"].create({
            "name": "Dashboard Access Section",
            "program_id": cls.program.id,
            "semester_id": cls.semester.id,
            "teacher_id": cls.teacher.id,
        })
        cls.other_section = cls.env["university.class.section"].create({
            "name": "Dashboard Access Other Section",
            "program_id": cls.other_program.id,
            "semester_id": cls.semester.id,
            "teacher_id": cls.other_teacher.id,
        })

        cls.user_student = cls._create_user("dashboard.access.student", cls.group_student)
        cls.student = cls._create_student(
            "Dashboard Access Student", "DASH-ACCESS-S1", cls.user_student,
            cls.program, cls.department,
        )
        cls.other_student_user = cls._create_user(
            "dashboard.access.other.student", cls.group_student,
        )
        cls.other_student = cls._create_student(
            "Dashboard Access Other Student", "DASH-ACCESS-S2", cls.other_student_user,
            cls.other_program, cls.other_department,
        )
        for student, program, section in (
            (cls.student, cls.program, cls.section),
            (cls.other_student, cls.other_program, cls.other_section),
        ):
            cls.env["university.enrollment"].create({
                "student_id": student.id,
                "program_id": program.id,
                "section_id": section.id,
                "semester_id": cls.semester.id,
                "academic_year_id": cls.year.id,
                "status": "enrolled",
            })

        cls.user_admin = cls._create_user("dashboard.access.admin", cls.group_admin)
        cls.user_without_student = cls._create_user(
            "dashboard.access.no.student", None,
        )

    @classmethod
    def _create_user(cls, login, group):
        groups = [cls.group_user.id]
        if group:
            groups.append(group.id)
        return cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": login,
            "login": login,
            "email": f"{login}@example.test",
            "group_ids": [(6, 0, groups)],
        })

    @classmethod
    def _create_teacher(cls, name, user, department, staff_id):
        teacher = cls.env["university.teacher"].create({
            "name": name,
            "teacher_id": staff_id,
            "user_id": user.id,
            "department_id": department.id,
        })
        user.sudo().write({"teacher_id": teacher.id})
        return teacher

    @classmethod
    def _create_student(cls, name, student_id, user, program, department):
        return cls.env["university.student"].create({
            "name": name,
            "student_id": student_id,
            "user_id": user.id,
            "program_id": program.id,
            "department_id": department.id,
        })

    def test_student_cannot_request_another_student(self):
        dashboard = self.env["school.dashboard"].with_user(self.user_student)
        with self.assertRaises(AccessError):
            dashboard.get_student_dashboard_data(student_id=self.other_student.id)

    def test_student_without_requested_id_gets_own_dashboard(self):
        payload = self.env["school.dashboard"].with_user(
            self.user_student,
        ).get_student_dashboard_data()
        self.assertEqual(payload["student_view"]["student"]["id"], self.student.id)

    def test_internal_user_without_student_profile_is_denied(self):
        with self.assertRaises(AccessError):
            self.env["school.dashboard"].with_user(
                self.user_without_student,
            ).get_student_dashboard_data()

    def test_admin_can_request_any_student(self):
        payload = self.env["school.dashboard"].with_user(
            self.user_admin,
        ).get_student_dashboard_data(student_id=self.other_student.id)
        self.assertEqual(payload["student_view"]["student"]["id"], self.other_student.id)

    def test_teacher_can_request_student_in_own_section(self):
        payload = self.env["school.dashboard"].with_user(
            self.user_teacher,
        ).get_student_dashboard_data(student_id=self.student.id)
        self.assertEqual(payload["student_view"]["student"]["id"], self.student.id)

    def test_teacher_cannot_request_student_in_another_teachers_section(self):
        with self.assertRaises(AccessError):
            self.env["school.dashboard"].with_user(
                self.user_teacher,
            ).get_student_dashboard_data(student_id=self.other_student.id)

    def test_teacher_cannot_request_another_teacher_dashboard(self):
        with self.assertRaises(AccessError):
            self.env["school.dashboard"].with_user(
                self.user_teacher,
            ).get_teacher_dashboard_data(teacher_id=self.other_teacher.id)

    def test_hod_student_dashboard_respects_department_visibility(self):
        dashboard = self.env["school.dashboard"].with_user(self.user_hod)
        own_payload = dashboard.get_student_dashboard_data(student_id=self.student.id)
        self.assertEqual(own_payload["student_view"]["student"]["id"], self.student.id)
        with self.assertRaises(AccessError):
            dashboard.get_student_dashboard_data(student_id=self.other_student.id)
