from uuid import uuid4

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestClassSectionAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        code = uuid4().hex[:10]
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_teacher = cls.env.ref("school_management.group_school_teacher")
        cls.group_hod = cls.env.ref("school_management.group_school_hod")
        cls.group_admin = cls.env.ref("school_management.group_school_admin")

        cls.academic_year = cls.env["university.academic.year"].create({
            "name": "Class Access AY %s" % code,
            "date_start": "2030-09-01",
            "date_end": "2031-06-30",
            "current": False,
        })
        cls.semester = cls.env["university.semester"].create({
            "name": "Class Access Semester %s" % code,
            "academic_year_id": cls.academic_year.id,
            "semester_type": "semester_1",
            "date_start": "2030-09-01",
            "date_end": "2031-01-31",
        })
        cls.faculty = cls.env["university.faculty"].create({
            "name": "Class Access Faculty %s" % code,
            "code": "CAF-%s" % code,
        })
        cls.department = cls.env["university.department"].create({
            "name": "Class Access Department %s" % code,
            "code": "CAD-%s" % code,
            "faculty_id": cls.faculty.id,
        })
        cls.program = cls.env["university.program"].create({
            "name": "Class Access Program %s" % code,
            "code": "CAP-%s" % code,
            "department_id": cls.department.id,
        })

        cls.user_teacher_a = cls._create_user("class.access.teacher.a.%s" % code, cls.group_teacher)
        cls.user_teacher_b = cls._create_user("class.access.teacher.b.%s" % code, cls.group_teacher)
        cls.user_hod = cls._create_user("class.access.hod.%s" % code, cls.group_hod)
        cls.user_admin = cls._create_user("class.access.admin.%s" % code, cls.group_admin)

        cls.teacher_a = cls.env["university.teacher"].create({
            "name": "Class Access Teacher A %s" % code,
            "user_id": cls.user_teacher_a.id,
            "department_id": cls.department.id,
        })
        cls.teacher_b = cls.env["university.teacher"].create({
            "name": "Class Access Teacher B %s" % code,
            "user_id": cls.user_teacher_b.id,
            "department_id": cls.department.id,
        })
        cls.teacher_hod = cls.env["university.teacher"].create({
            "name": "Class Access HOD %s" % code,
            "user_id": cls.user_hod.id,
            "department_id": cls.department.id,
        })
        cls.env["university.academic.assignment"].create({
            "staff_id": cls.teacher_hod.id,
            "department_id": cls.department.id,
            "role": "department_head",
            "active": True,
            "start_date": fields.Date.today(),
        })
        cls.teacher_hod._compute_managed_scopes()
        cls.department._compute_head_id()

        cls.section_a = cls.env["university.class.section"].create({
            "name": "Class Access A %s" % code,
            "program_id": cls.program.id,
            "semester_id": cls.semester.id,
            "teacher_id": cls.teacher_a.id,
        })
        cls.section_b = cls.env["university.class.section"].create({
            "name": "Class Access B %s" % code,
            "program_id": cls.program.id,
            "semester_id": cls.semester.id,
            "teacher_id": cls.teacher_b.id,
        })
        cls.section_unassigned = cls.env["university.class.section"].create({
            "name": "Class Access Unassigned %s" % code,
            "program_id": cls.program.id,
            "semester_id": cls.semester.id,
        })

    @classmethod
    def _create_user(cls, login, group):
        return cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": login,
            "login": login,
            "email": "%s@university.edu" % login,
            "group_ids": [(6, 0, [cls.group_user.id, group.id])],
        })

    def test_teacher_access_is_limited_to_assigned_sections(self):
        model = self.env["university.class.section"]
        teacher_a_sections = model.with_user(self.user_teacher_a).search([])
        self.assertIn(self.section_a, teacher_a_sections)
        self.assertNotIn(self.section_b, teacher_a_sections)
        self.assertNotIn(self.section_unassigned, teacher_a_sections)
        with self.assertRaises(AccessError):
            self.section_b.with_user(self.user_teacher_a).read()
        with self.assertRaises(AccessError):
            self.section_unassigned.with_user(self.user_teacher_a).read()

        teacher_b_sections = model.with_user(self.user_teacher_b).search([])
        self.assertIn(self.section_b, teacher_b_sections)
        self.assertNotIn(self.section_a, teacher_b_sections)

    def test_hod_and_admin_scopes_are_preserved(self):
        model = self.env["university.class.section"]
        hod_sections = model.with_user(self.user_hod).search([])
        self.assertIn(self.section_a, hod_sections)
        self.assertIn(self.section_b, hod_sections)
        self.assertIn(self.section_unassigned, hod_sections)

        admin_sections = model.with_user(self.user_admin).search([])
        self.assertIn(self.section_a, admin_sections)
        self.assertIn(self.section_b, admin_sections)
        self.assertIn(self.section_unassigned, admin_sections)
