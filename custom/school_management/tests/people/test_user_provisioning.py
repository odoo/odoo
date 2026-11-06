from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestUserProvisioning(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Users = self.env["res.users"].sudo()
        self.Student = self.env["university.student"].sudo()
        self.Teacher = self.env["university.teacher"].sudo()

        self.student_group = self.env.ref("school_management.group_school_student")
        self.teacher_group = self.env.ref("school_management.group_school_teacher")
        self.dashboard_group = self.env.ref("school_management.group_teacher_dashboard")
        self.admin_group = self.env.ref("school_management.group_school_admin")
        self.internal_group = self.env.ref("base.group_user")

        # Create an admin user for testing
        self.admin_user = self.Users.with_context(no_reset_password=True).create(
            {
                "name": "Admin Tester",
                "login": "admin_tester@example.com",
                "email": "admin_tester@example.com",
                "group_ids": [(6, 0, [self.internal_group.id, self.admin_group.id])],
            }
        )

        # Create a non-admin user (plain student)
        self.plain_user = self.Users.with_context(no_reset_password=True).create(
            {
                "name": "Plain User",
                "login": "plain_user@example.com",
                "email": "plain_user@example.com",
                "group_ids": [(6, 0, [self.internal_group.id, self.student_group.id])],
            }
        )

    # -------------------------------------------------------------------------
    # Student Provisioning Tests
    # -------------------------------------------------------------------------

    def test_student_action_create_user_success(self):
        student = self.Student.create({
            "name": "Test Student Provisioning",
            "email": "test.provisioning.student@example.com",
        })

        # Run as admin
        res = student.with_user(self.admin_user).action_create_user()
        self.assertEqual(res.get("type"), "ir.actions.client")
        self.assertEqual(res.get("tag"), "display_notification")

        self.assertTrue(student.user_id)
        user = student.user_id
        self.assertEqual(user.login, "test.provisioning.student@example.com")
        self.assertEqual(user.email, "test.provisioning.student@example.com")
        self.assertIn(self.internal_group, user.group_ids)
        self.assertIn(self.student_group, user.group_ids)

    def test_student_action_create_user_missing_email(self):
        student = self.Student.create({
            "name": "Student Without Email",
        })
        with self.assertRaises(UserError):
            student.with_user(self.admin_user).action_create_user()

    def test_student_action_create_user_already_linked(self):
        student = self.Student.create({
            "name": "Already Linked Student",
            "email": "already.linked@example.com",
            "user_id": self.plain_user.id,
        })
        with self.assertRaises(UserError):
            student.with_user(self.admin_user).action_create_user()

    def test_student_action_create_user_non_admin_forbidden(self):
        student = self.Student.create({
            "name": "Student Security Check",
            "email": "sec.check@example.com",
        })
        with self.assertRaises(AccessError):
            student.with_user(self.plain_user).action_create_user()

    def test_student_action_reset_password(self):
        student = self.Student.create({
            "name": "Reset Password Student",
            "email": "reset.student@example.com",
        })
        student.with_user(self.admin_user).action_create_user()
        self.assertTrue(student.user_id)

        res = student.with_user(self.admin_user).action_reset_password()
        self.assertEqual(res.get("type"), "ir.actions.client")
        self.assertEqual(res.get("tag"), "display_notification")

    # -------------------------------------------------------------------------
    # Teacher Provisioning Tests
    # -------------------------------------------------------------------------

    def test_teacher_action_create_user_success(self):
        teacher = self.Teacher.create({
            "name": "Test Teacher Provisioning",
            "email": "test.provisioning.teacher@example.com",
        })

        res = teacher.with_user(self.admin_user).action_create_user()
        self.assertEqual(res.get("type"), "ir.actions.client")
        self.assertEqual(res.get("tag"), "display_notification")

        self.assertTrue(teacher.user_id)
        user = teacher.user_id
        self.assertEqual(user.login, "test.provisioning.teacher@example.com")
        self.assertEqual(user.email, "test.provisioning.teacher@example.com")
        self.assertIn(self.internal_group, user.group_ids)
        self.assertIn(self.teacher_group, user.group_ids)
        self.assertIn(self.dashboard_group, user.group_ids)

        # Verify reciprocal linking!
        self.assertEqual(user.teacher_id, teacher)
        self.assertEqual(teacher.user_id, user)

    def test_teacher_action_create_user_missing_email(self):
        teacher = self.Teacher.create({
            "name": "Teacher Without Email",
        })
        with self.assertRaises(UserError):
            teacher.with_user(self.admin_user).action_create_user()

    def test_teacher_action_create_user_non_admin_forbidden(self):
        teacher = self.Teacher.create({
            "name": "Teacher Security Check",
            "email": "teacher.sec@example.com",
        })
        with self.assertRaises(AccessError):
            teacher.with_user(self.plain_user).action_create_user()

    def test_teacher_action_reset_password(self):
        teacher = self.Teacher.create({
            "name": "Reset Password Teacher",
            "email": "reset.teacher@example.com",
        })
        teacher.with_user(self.admin_user).action_create_user()
        self.assertTrue(teacher.user_id)

        res = teacher.with_user(self.admin_user).action_reset_password()
        self.assertEqual(res.get("type"), "ir.actions.client")
        self.assertEqual(res.get("tag"), "display_notification")
