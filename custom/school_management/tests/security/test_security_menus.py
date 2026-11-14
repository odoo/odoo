from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestSecurityMenus(TransactionCase):
    """Verify the role/menu/security architecture behaves correctly.

    Fixes regressions where non-admin school roles could not see the
    University app/dashboard, and where users could reach menus whose
    underlying models they could not read (AccessError).
    """

    def setUp(self):
        super().setUp()
        self.Users = self.env["res.users"].sudo()
        self.Faculty = self.env["university.faculty"].sudo()
        self.Department = self.env["university.department"].sudo()
        self.Program = self.env["university.program"].sudo()
        self.Student = self.env["university.student"].sudo()
        self.Teacher = self.env["university.teacher"].sudo()
        self.ClassSection = self.env["university.class.section"].sudo()
        self.Enrollment = self.env["university.enrollment"].sudo()
        self.Dashboard = self.env["school.dashboard"].sudo()

        self.g_user = self.env.ref("school_management.group_school_user")
        self.g_student = self.env.ref("school_management.group_school_student")
        self.g_teacher = self.env.ref("school_management.group_school_teacher")
        self.g_hod = self.env.ref("school_management.group_school_hod")
        self.g_dean = self.env.ref("school_management.group_school_dean")
        self.g_admin = self.env.ref("school_management.group_school_admin")

        self.root_menu = self.env.ref("school_management.menu_school_root")
        self.dashboard_menu = self.env.ref("school_management.menu_school_dashboard")
        self.student_dashboard_menu = self.env.ref("school_management.menu_student_dashboard")
        self.finance_menu = self.env.ref("school_management.menu_university_finance_category")
        self.administration_menu = self.env.ref("school_management.menu_university_administration")
        self.signature_menu = self.env.ref("school_management.menu_university_document_signature")
        self.role_management_menu = self.env.ref("school_management.menu_university_role_management")
        self.student_menu = self.env.ref("school_management.menu_school_student_category")
        self.academic_year_menu = self.env.ref("school_management.menu_university_academic_year")
        self.subject_menu = self.env.ref("school_management.menu_university_subject")

    def _make_user(self, login, *groups):
        return self.Users.with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@example.com" % login,
                "group_ids": [(6, 0, [g.id for g in groups])],
            }
        )

    def _groups_visible(self, user):
        """True if any of a menu's groups is assigned (incl. implied) to user."""
        user_groups = user.group_ids
        return self.root_menu.group_ids & user_groups

    # ------------------------------------------------------------------ #
    # 1-4. Dashboard read access per role
    # ------------------------------------------------------------------ #
    def test_dashboard_readable_by_admin(self):
        user = self._make_user("a", self.g_admin)
        rec = self.Dashboard.with_user(user).search([], limit=1)
        self.assertTrue(rec)

    def test_dashboard_readable_by_teacher(self):
        user = self._make_user("t", self.g_teacher)
        rec = self.Dashboard.with_user(user).search([], limit=1)
        self.assertTrue(rec)

    def test_dashboard_readable_by_hod(self):
        user = self._make_user("h", self.g_hod)
        rec = self.Dashboard.with_user(user).search([], limit=1)
        self.assertTrue(rec)

    def test_dashboard_readable_by_dean(self):
        user = self._make_user("d", self.g_dean)
        rec = self.Dashboard.with_user(user).search([], limit=1)
        self.assertTrue(rec)

    def test_dashboard_readable_by_plain_school_user(self):
        user = self._make_user("su", self.g_user)
        rec = self.Dashboard.with_user(user).search([], limit=1)
        self.assertTrue(rec)

    def test_dashboard_counts_respect_scope_no_access_error(self):
        # A teacher has no fee ACL; the dashboard must not raise AccessError
        # when aggregating financial KPIs (regression for sudo() removal).
        user = self._make_user("t2", self.g_teacher)
        rec = self.Dashboard.with_user(user).search([], limit=1)
        self.assertTrue(rec)
        # Read the record to trigger compute fields safely.
        self.assertEqual(rec.with_user(user).fee_count, 0)

        with self.assertLogs("odoo.addons.school_management.models.dashboard", level="INFO") as logs:
            rec.with_user(user).invalidate_recordset()
            self.assertEqual(rec.with_user(user).fee_count, 0)
        self.assertTrue(any("university.fee" in message for message in logs.output))

    def test_dashboard_chart_data_respects_scope_without_access_error(self):
        user = self._make_user("t4", self.g_teacher)
        chart_data = self.Dashboard.with_user(user).get_chart_data()

        self.assertIn("program_distribution", chart_data)
        self.assertIn("student_status", chart_data)
        self.assertEqual(chart_data["recent_payments"], [])

    def test_university_admin_can_read_all_dashboard_sources(self):
        user = self._make_user("full_admin", self.g_admin)
        for model in (
            "university.faculty",
            "university.department",
            "university.program",
            "university.academic.year",
            "university.semester",
            "university.teacher",
            "university.student",
            "university.subject",
            "university.classroom",
            "university.class.section",
            "university.enrollment",
            "university.fee",
            "university.payment",
            "university.document.signature",
        ):
            records = self.env[model].with_user(user)
            self.assertTrue(records.has_access("read"), model)
            records.search([], limit=1)

    def test_university_admin_can_manage_users_and_roles(self):
        """University administrators receive the native Odoo role-management page."""
        user = self._make_user("role_admin", self.g_admin)
        self.assertTrue(user.has_group("base.group_system"))
        self.assertTrue(self.env["res.users"].with_user(user).has_access("write"))
        self.assertTrue(self.env["res.groups"].with_user(user).has_access("write"))
        self.assertEqual(
            self.role_management_menu.action,
            self.env.ref("base.action_res_users"),
        )
        self.assertIn(self.g_admin, self.role_management_menu.group_ids)

    # ------------------------------------------------------------------ #
    # 5. Unauthorized user cannot read protected finance models
    # ------------------------------------------------------------------ #
    def test_teacher_cannot_read_fee(self):
        user = self._make_user("t3", self.g_teacher)
        with self.assertRaises(AccessError):
            self.env["university.fee"].with_user(user).search([], limit=1)

    def test_student_cannot_read_academic_assignment(self):
        user = self._make_user("s3", self.g_student)
        with self.assertRaises(AccessError):
            self.env["university.academic.assignment"].with_user(user).search([], limit=1)

    def test_student_cannot_write_academic_year(self):
        user = self._make_user("s4", self.g_student)
        year = self.env["university.academic.year"].search([], limit=1)
        if year:
            with self.assertRaises(AccessError):
                year.with_user(user).write({"name": "Unauthorized Edit"})

    def test_student_sees_only_the_linked_student_record(self):
        user = self._make_user("student_scope", self.g_student)
        own_student = self.Student.create(
            {"name": "Own Student", "user_id": user.id}
        )
        other_student = self.Student.create({"name": "Other Student"})

        visible = self.Student.with_user(user).search([])

        self.assertIn(own_student, visible)
        self.assertNotIn(other_student, visible)

    # ------------------------------------------------------------------ #
    # Root menu visibility per role
    # ------------------------------------------------------------------ #
    def test_root_menu_groups_include_school_user_and_system(self):
        menu_groups = self.root_menu.group_ids
        self.assertIn(self.g_user, menu_groups)
        system = self.env.ref("base.group_system")
        self.assertIn(system, menu_groups)

    def test_university_root_and_dashboard_menu_open_dashboard_action(self):
        dashboard_action = self.env.ref("school_management.action_school_dashboard_shell")
        legacy_dashboard_action = self.env.ref("school_management.action_school_dashboard")
        department_action = self.env.ref("school_management.action_university_department")

        self.assertEqual(self.root_menu.action, dashboard_action)
        self.assertEqual(self.dashboard_menu.action, dashboard_action)
        self.assertEqual(dashboard_action.type, "ir.actions.client")
        self.assertEqual(dashboard_action.tag, "school_dashboard_shell")
        self.assertNotEqual(dashboard_action, department_action)
        self.assertFalse(
            any(menu.action == legacy_dashboard_action for menu in self.env["ir.ui.menu"].search([])),
            "The legacy school.dashboard action must not be attached to a menu",
        )

    def test_dashboard_is_the_single_student_home(self):
        """Students enter through Dashboard; the old portal item stays retired."""
        self.assertIn(self.g_student, self.dashboard_menu.group_ids)
        self.assertFalse(self.student_dashboard_menu.active)

    def test_root_menu_visible_to_teacher_hod_dean_admin(self):
        for group in (self.g_teacher, self.g_hod, self.g_dean, self.g_admin):
            user = self._make_user("m_%s" % group.id, group)
            self.assertTrue(
                self._groups_visible(user),
                "%s should see the University root menu" % group.name,
            )

    # ------------------------------------------------------------------ #
    # Finance menu is admin-only (no AccessError for staff)
    # ------------------------------------------------------------------ #
    def test_finance_menu_admin_only(self):
        finance_groups = self.finance_menu.group_ids
        signature_groups = self.signature_menu.group_ids
        system = self.env.ref("base.group_system")
        self.assertIn(self.g_admin, finance_groups)
        self.assertIn(self.g_admin, signature_groups)
        self.assertIn(system, finance_groups)
        self.assertIn(system, signature_groups)
        self.assertNotIn(self.g_teacher, finance_groups)
        self.assertNotIn(self.g_teacher, signature_groups)
        self.assertNotIn(self.g_dean, finance_groups)
        self.assertNotIn(self.g_dean, signature_groups)

    def test_document_signature_menu_opens_administration_action(self):
        action = self.env.ref("school_management.action_university_document_signature")
        system = self.env.ref("base.group_system")
        documents_menu = self.env.ref("school_management.menu_university_documents")

        self.assertEqual(self.signature_menu.parent_id, documents_menu)
        self.assertEqual(documents_menu.parent_id, self.administration_menu)
        self.assertEqual(self.signature_menu.action, action)
        self.assertEqual(action.res_model, "university.document.signature")
        self.assertIn(self.g_admin, self.signature_menu.group_ids)
        self.assertIn(system, self.signature_menu.group_ids)

    def test_academic_year_menu_admin_only(self):
        groups = self.academic_year_menu.group_ids
        self.assertIn(self.g_admin, groups)
        self.assertNotIn(self.g_teacher, groups)

    def test_student_menu_visible_to_teacher(self):
        self.assertIn(self.g_teacher, self.student_menu.group_ids)

    def test_subject_menu_visible_to_teacher(self):
        self.assertIn(self.g_teacher, self.subject_menu.group_ids)

    # ------------------------------------------------------------------ #
    # Record rules still scope data by role
    # ------------------------------------------------------------------ #
    def _scope_setup(self):
        fac_a = self.Faculty.create({"name": "FacA", "code": "FA_SCOPE"})
        fac_b = self.Faculty.create({"name": "FacB", "code": "FB_SCOPE"})
        dep_a = self.Department.create({"name": "DepA", "code": "DA_SCOPE", "faculty_id": fac_a.id})
        dep_b = self.Department.create({"name": "DepB", "code": "DB_SCOPE", "faculty_id": fac_b.id})
        prog_a = self.Program.create({"name": "PA", "code": "PA_SCOPE", "department_id": dep_a.id})
        prog_b = self.Program.create({"name": "PB", "code": "PB_SCOPE", "department_id": dep_b.id})

        hod = self.Teacher.create({"name": "HOD", "department_id": dep_a.id})
        hod_user = self._make_user("hod2", self.g_hod)
        hod.user_id = hod_user
        assignment_model = self.env["university.academic.assignment"].sudo()
        assignment_model.create(
            {
                "name": "HOD A",
                "staff_id": hod.id,
                "role": "department_head",
                "department_id": dep_a.id,
                "start_date": "2025-01-01",
            }
        )
        # A teacher in dept A owns a section under dept A's program
        teacher = self.Teacher.create({"name": "TeachA", "department_id": dep_a.id})
        teacher_user = self._make_user("teacher2", self.g_teacher)
        teacher.user_id = teacher_user

        year = self.env["university.academic.year"].search([("name", "=", "2034-2035")], limit=1)
        if not year:
            year = self.env["university.academic.year"].create(
                {"name": "2034-2035", "date_start": "2034-09-01", "date_end": "2035-06-30"}
            )
        sem = self.env["university.semester"].create(
            {
                "name": "S1",
                "academic_year_id": year.id,
                "semester_type": "semester_1",
                "date_start": "2034-09-01",
                "date_end": "2034-12-22",
            }
        )
        section_a = self.env["university.class.section"].sudo().create(
            {"name": "SEC-A", "program_id": prog_a.id, "semester_id": sem.id, "teacher_id": teacher.id}
        )
        section_b = self.env["university.class.section"].sudo().create(
            {"name": "SEC-B", "program_id": prog_b.id, "semester_id": sem.id}
        )
        return fac_a, fac_b, dep_a, dep_b, prog_a, prog_b, hod, hod_user, teacher, teacher_user, section_a, section_b

    def test_hod_sees_own_department_sections_only(self):
        (fac_a, fac_b, dep_a, dep_b, prog_a, prog_b,
         hod, hod_user, teacher, teacher_user, section_a, section_b) = self._scope_setup()
        visible = self.env["university.class.section"].sudo().with_user(hod_user).search([])
        self.assertIn(section_a, visible)
        self.assertNotIn(section_b, visible)

    def test_teacher_sees_own_sections_only(self):
        (fac_a, fac_b, dep_a, dep_b, prog_a, prog_b,
         hod, hod_user, teacher, teacher_user, section_a, section_b) = self._scope_setup()
        visible = self.env["university.class.section"].sudo().with_user(teacher_user).search([])
        self.assertIn(section_a, visible)
        self.assertNotIn(section_b, visible)

    def test_student_sees_only_enrolled_class_sections(self):
        (
            _fac_a,
            _fac_b,
            _dep_a,
            _dep_b,
            prog_a,
            _prog_b,
            _hod,
            _hod_user,
            _teacher,
            _teacher_user,
            section_a,
            section_b,
        ) = self._scope_setup()
        student_user = self._make_user("student_sections", self.g_student)
        student = self.Student.create(
            {
                "name": "Student Sections",
                "program_id": prog_a.id,
                "user_id": student_user.id,
            }
        )
        self.Enrollment.create(
            {
                "student_id": student.id,
                "class_section_id": section_a.id,
                "status": "enrolled",
            }
        )

        visible = self.ClassSection.with_user(student_user).search([])
        self.assertIn(section_a, visible)
        self.assertNotIn(section_b, visible)
