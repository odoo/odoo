from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestStudentSignup(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Users = self.env["res.users"].sudo()
        self.Student = self.env["university.student"].sudo()
        self.student_group = self.env.ref("school_management.group_school_student")
        self.portal_group = self.env.ref("base.group_portal")
        self.internal_group = self.env.ref("base.group_user")

    def test_signup_links_existing_student(self):
        student = self.Student.create(
            {
                "name": "Signup Student",
                "email": "signup.student@example.com",
            }
        )

        login, password = self.Users.signup(
            {
                "login": "signup.student@example.com",
                "name": "Signup Student",
                "password": "Student@123",
            }
        )

        user = self.Users.search([("login", "=", login)], limit=1)
        self.assertEqual(password, "Student@123")
        self.assertEqual(student.user_id, user)
        self.assertFalse(user.share, "Sign-up students must be internal backend users")
        self.assertNotIn(self.portal_group, user.group_ids)
        self.assertIn(self.internal_group, user.group_ids)
        self.assertIn(self.student_group, user.group_ids)

    def test_signup_student_reads_only_own_record(self):
        student = self.Student.create(
            {
                "name": "Portal Student",
                "email": "portal.student@example.com",
            }
        )
        other = self.Student.create(
            {
                "name": "Other Student",
                "email": "other.student@example.com",
            }
        )

        login, _password = self.Users.signup(
            {
                "login": "portal.student@example.com",
                "name": "Portal Student",
                "password": "Student@123",
            }
        )
        user = self.Users.search([("login", "=", login)], limit=1)

        # Own record is readable through the student backend user environment.
        own = self.Student.with_user(user).search(
            [("id", "=", student.id)]
        )
        self.assertEqual(len(own), 1)

        # Another student's record is neither readable...
        others = self.Student.with_user(user).search(
            [("id", "=", other.id)]
        )
        self.assertFalse(others, "A student must never see other student records")

        # ...nor writable, even on their own record (read-only ACL).
        with self.assertRaises(AccessError):
            self.Student.with_user(user).browse(own.id).write({"notes": "hacked"})

        with self.assertRaises(AccessError):
            self.Student.with_user(user).create(
                {"name": "Rogue Student", "email": "rogue@example.com"}
            )

    def test_signup_requires_existing_student(self):
        with self.assertRaises(UserError):
            self.Users.signup(
                {
                    "login": "missing.student@example.com",
                    "name": "Missing Student",
                    "password": "Student@123",
                }
            )

    def test_signup_rejects_already_linked_student(self):
        existing_user = self.Users.with_context(no_reset_password=True).create(
            {
                "name": "Existing Login",
                "login": "claimed.student@example.com",
                "email": "claimed.student@example.com",
                "group_ids": [(6, 0, [self.student_group.id])],
            }
        )
        self.Student.create(
            {
                "name": "Claimed Student",
                "email": "claimed.student@example.com",
                "user_id": existing_user.id,
            }
        )

        with self.assertRaises(UserError):
            self.Users.signup(
                {
                    "login": "claimed.student@example.com",
                    "name": "Claimed Student",
                    "password": "Student@123",
                }
            )

    def test_student_user_cannot_open_admin_academic_years(self):
        student_user = self.Users.with_context(no_reset_password=True).create(
            {
                "name": "Portal Student",
                "login": "portal.student@example.com",
                "email": "portal.student@example.com",
                "group_ids": [(6, 0, [self.student_group.id])],
            }
        )

        with self.assertRaises(AccessError):
            self.env["university.academic.year"].with_user(student_user).search([], limit=1)
