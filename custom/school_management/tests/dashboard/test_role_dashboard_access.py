from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestRoleDashboardAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.academic_year = cls.env["university.academic.year"].create({
            "name": "AY-TEST-ROLE-2026",
            "date_start": "2026-09-01",
            "date_end": "2027-06-30",
            "active": True,
            "current": True,
        })
        cls.semester = cls.env["university.semester"].create({
            "name": "Semester Test Role 1 2026",
            "academic_year_id": cls.academic_year.id,
            "semester_type": "semester_1",
            "date_start": "2026-09-01",
            "date_end": "2027-01-31",
            "active": True,
        })

        cls.faculty_eng = cls.env["university.faculty"].create({
            "name": "Role Faculty Engineering",
            "code": "ROLE-ENG",
        })
        cls.faculty_biz = cls.env["university.faculty"].create({
            "name": "Role Faculty Business",
            "code": "ROLE-BIZ",
        })

        cls.dept_cs = cls.env["university.department"].create({
            "name": "Role Computer Science",
            "code": "ROLE-CS",
            "faculty_id": cls.faculty_eng.id,
        })
        cls.dept_mgmt = cls.env["university.department"].create({
            "name": "Role Management",
            "code": "ROLE-MGMT",
            "faculty_id": cls.faculty_biz.id,
        })

        cls.program_cs = cls.env["university.program"].create({
            "name": "Role B.Sc. Computer Science",
            "code": "ROLE-BSCS",
            "department_id": cls.dept_cs.id,
        })
        cls.program_mgmt = cls.env["university.program"].create({
            "name": "Role BBA Management",
            "code": "ROLE-BBA",
            "department_id": cls.dept_mgmt.id,
        })

        # Security groups
        cls.group_admin = cls.env.ref("school_management.group_school_admin")
        cls.group_dean = cls.env.ref("school_management.group_school_dean")
        cls.group_hod = cls.env.ref("school_management.group_school_hod")
        cls.group_registrar = cls.env.ref("school_management.group_school_registrar")
        cls.group_teacher = cls.env.ref("school_management.group_school_teacher")
        cls.group_teacher_alias = cls.env.ref("school_management.group_university_teacher")
        cls.group_student = cls.env.ref("school_management.group_school_student")
        cls.group_system = cls.env.ref("base.group_system")
        cls.group_user = cls.env.ref("base.group_user")

        # 1. Admin user
        cls.user_admin = cls._create_user("role.test.admin", [cls.group_admin.id])

        # 2. HOD CS user & teacher
        cls.user_hod = cls._create_user("role.test.hod_cs", [cls.group_hod.id])
        cls.teacher_hod = cls.env["university.teacher"].create({
            "name": "Dr. HOD CS",
            "teacher_id": "ROLE-THOD-01",
            "user_id": cls.user_hod.id,
            "department_id": cls.dept_cs.id,
        })
        cls.env["university.academic.assignment"].create({
            "staff_id": cls.teacher_hod.id,
            "department_id": cls.dept_cs.id,
            "role": "department_head",
            "active": True,
            "start_date": "2026-01-01",
        })
        cls.teacher_hod._compute_managed_scopes()
        cls.dept_cs._compute_head_id()
        cls.user_hod.sudo().write({"teacher_id": cls.teacher_hod.id})

        # 3. Head of Faculty user & teacher.  This role inherits HOD, so its
        # dashboard must still be identified as faculty-level rather than HOD.
        cls.user_dean = cls._create_user("role.test.dean_eng", [cls.group_dean.id])
        cls.teacher_dean = cls.env["university.teacher"].create({
            "name": "Dr. Faculty Head Engineering",
            "teacher_id": "ROLE-TDEAN-01",
            "user_id": cls.user_dean.id,
            "department_id": cls.dept_cs.id,
        })
        cls.env["university.academic.assignment"].create({
            "staff_id": cls.teacher_dean.id,
            "faculty_id": cls.faculty_eng.id,
            "role": "dean",
            "start_date": "2026-01-01",
        })
        cls.teacher_dean._compute_managed_scopes()
        cls.user_dean.sudo().write({"teacher_id": cls.teacher_dean.id})

        # 4. Registrar user.  This role is independent of the teaching chain.
        cls.user_registrar = cls._create_user("role.test.registrar", [cls.group_registrar.id])

        # 5. Teacher CS user
        cls.user_teacher_cs = cls._create_user("role.test.teacher_cs", [cls.group_teacher.id])
        cls.teacher_cs = cls.env["university.teacher"].create({
            "name": "Prof. Alan Turing",
            "teacher_id": "ROLE-TCS-01",
            "user_id": cls.user_teacher_cs.id,
            "department_id": cls.dept_cs.id,
        })
        cls.user_teacher_cs.sudo().write({"teacher_id": cls.teacher_cs.id})

        # Section for CS
        cls.section_cs = cls.env["university.class.section"].create({
            "name": "ROLE-CS-101",
            "program_id": cls.program_cs.id,
            "semester_id": cls.semester.id,
            "teacher_id": cls.teacher_cs.id,
        })

        # 6. Teacher MGMT user (unrelated department)
        cls.user_teacher_mgmt = cls._create_user("role.test.teacher_mgmt", [cls.group_teacher.id])
        cls.teacher_mgmt = cls.env["university.teacher"].create({
            "name": "Dr. Peter Drucker",
            "teacher_id": "ROLE-TMGMT-01",
            "user_id": cls.user_teacher_mgmt.id,
            "department_id": cls.dept_mgmt.id,
        })
        cls.user_teacher_mgmt.sudo().write({"teacher_id": cls.teacher_mgmt.id})

        # 7. Students in CS
        cls.user_student1 = cls._create_user("role.test.student1_cs", [cls.group_student.id])
        cls.student_cs1 = cls.env["university.student"].create({
            "name": "Alice CS",
            "student_id": "ROLE-SCS-001",
            "user_id": cls.user_student1.id,
            "program_id": cls.program_cs.id,
            "advisor_id": cls.teacher_cs.id,
            "academic_year_id": cls.academic_year.id,
            "current_semester_id": cls.semester.id,
        })

        cls.student_cs2 = cls.env["university.student"].create({
            "name": "Bob CS",
            "student_id": "ROLE-SCS-002",
            "program_id": cls.program_cs.id,
            "academic_year_id": cls.academic_year.id,
            "current_semester_id": cls.semester.id,
        })

        # 8. Student in MGMT
        cls.user_student_mgmt = cls._create_user("role.test.student_mgmt", [cls.group_student.id])
        cls.student_mgmt = cls.env["university.student"].create({
            "name": "Charlie Biz",
            "student_id": "ROLE-SBM-001",
            "user_id": cls.user_student_mgmt.id,
            "program_id": cls.program_mgmt.id,
            "advisor_id": cls.teacher_mgmt.id,
            "academic_year_id": cls.academic_year.id,
            "current_semester_id": cls.semester.id,
        })

    @classmethod
    def _create_user(cls, login, group_ids):
        return cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": login,
            "login": login,
            "email": f"{login}@university.edu",
            "group_ids": [(6, 0, [cls.group_user.id] + group_ids)],
        })

    def test_01_admin_full_access(self):
        """Admin has global access across all students, departments, and teachers without sudo."""
        student_model = self.env["university.student"].with_user(self.user_admin)
        students = student_model.search([])
        self.assertIn(self.student_cs1, students)
        self.assertIn(self.student_cs2, students)
        self.assertIn(self.student_mgmt, students)

        # Admin can assign advisors freely
        self.student_cs2.with_user(self.user_admin).write({"advisor_id": self.teacher_cs.id})
        self.assertEqual(self.student_cs2.advisor_id, self.teacher_cs)

        # Admin can retrieve global dashboard data
        dashboard_data = self.env["school.dashboard"].with_user(self.user_admin).get_role_dashboard_data()
        self.assertEqual(dashboard_data["dashboard"]["user_role"], "admin")
        self.assertGreaterEqual(dashboard_data["dashboard"]["student_count"], 3)

    def test_01_system_user_with_teacher_group_uses_admin_dashboard(self):
        """A system user must not be routed to teacher dashboard data."""
        user = self._create_user(
            "role.test.system_teacher",
            [self.group_system.id, self.group_teacher_alias.id],
        )
        dashboard_data = self.env["school.dashboard"].with_user(user).get_role_dashboard_data()

        self.assertEqual(dashboard_data["dashboard"]["user_role"], "admin")

    def test_02_hod_department_scoping(self):
        """HOD can access only their managed department records, not other departments."""
        student_model = self.env["university.student"].with_user(self.user_hod)
        students = student_model.search([])
        self.assertIn(self.student_cs1, students)
        self.assertIn(self.student_cs2, students)
        self.assertNotIn(self.student_mgmt, students)

        # HOD sees only teachers in managed department
        teacher_model = self.env["university.teacher"].with_user(self.user_hod)
        teachers = teacher_model.search([])
        self.assertIn(self.teacher_cs, teachers)
        self.assertNotIn(self.teacher_mgmt, teachers)

        # HOD can assign advisors within their department
        self.student_cs2.with_user(self.user_hod).write({"advisor_id": self.teacher_cs.id})
        self.assertEqual(self.student_cs2.advisor_id, self.teacher_cs)

        # HOD cannot assign an advisor from another department
        with self.assertRaises(AccessError):
            self.student_cs2.with_user(self.user_hod).write({"advisor_id": self.teacher_mgmt.id})

        # HOD cannot assign advisor for a student in another department
        with self.assertRaises(AccessError):
            self.student_mgmt.with_user(self.user_hod).write({"advisor_id": self.teacher_cs.id})

        # HOD dashboard returns department-scoped analytics
        dashboard_data = self.env["school.dashboard"].with_user(self.user_hod).get_role_dashboard_data()
        self.assertEqual(dashboard_data["dashboard"]["user_role"], "hod")
        self.assertEqual(dashboard_data["dashboard"]["student_count"], 2)

    def test_03_teacher_advisee_and_advising_scoping(self):
        """Teacher can see assigned advisees and record notes, but not unrelated students."""
        student_model = self.env["university.student"].with_user(self.user_teacher_cs)
        students = student_model.search([])
        self.assertIn(self.student_cs1, students)
        self.assertNotIn(self.student_cs2, students)
        self.assertNotIn(self.student_mgmt, students)

        # Teacher cannot reassign advisors
        with self.assertRaises(AccessError):
            self.student_cs1.with_user(self.user_teacher_cs).write({"advisor_id": self.teacher_hod.id})

        # Teacher can create an advising note for advisee
        note_model = self.env["university.student.advising.note"].with_user(self.user_teacher_cs)
        note = note_model.create({
            "student_id": self.student_cs1.id,
            "category": "academic",
            "note": "Meeting regarding course load.",
            "is_private": False,
        })
        self.assertEqual(note.advisor_id, self.teacher_cs)

        # Teacher cannot create note for unrelated student
        with self.assertRaises(AccessError):
            note_model.create({
                "student_id": self.student_mgmt.id,
                "note": "Illegal note",
            })

        # Teacher can create a followup action
        followup_model = self.env["university.student.followup"].with_user(self.user_teacher_cs)
        followup = followup_model.create({
            "student_id": self.student_cs1.id,
            "title": "Review midterm scores",
            "action_type": "meeting",
            "visible_to_student": True,
        })
        followup.action_start()
        self.assertEqual(followup.state, "in_progress")

    def test_04_private_advising_note_confidentiality(self):
        """Private notes are confidential and invisible to HOD and other advisors."""
        note_model = self.env["university.student.advising.note"]
        private_note = note_model.with_user(self.user_teacher_cs).create({
            "student_id": self.student_cs1.id,
            "category": "personal",
            "note": "Strictly confidential medical observation.",
            "is_private": True,
        })

        # Author teacher sees it
        self.assertIn(private_note, note_model.with_user(self.user_teacher_cs).search([]))

        # Admin sees it
        self.assertIn(private_note, note_model.with_user(self.user_admin).search([]))

        # HOD does NOT see the private note
        self.assertNotIn(private_note, note_model.with_user(self.user_hod).search([]))

        # Other teacher does NOT see it
        self.assertNotIn(private_note, note_model.with_user(self.user_teacher_mgmt).search([]))

        # Student CANNOT see advising notes
        with self.assertRaises(AccessError):
            note_model.with_user(self.user_student1).search([])

    def test_05_student_scoped_access(self):
        """Student sees only their personal profile and visible follow-ups, no other students."""
        student_model = self.env["university.student"].with_user(self.user_student1)
        students = student_model.search([])
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0], self.student_cs1)

        # Student sees visible follow-ups, but not hidden follow-ups
        followup_model = self.env["university.student.followup"]
        visible_followup = followup_model.with_user(self.user_admin).create({
            "student_id": self.student_cs1.id,
            "advisor_id": self.teacher_cs.id,
            "title": "Visible action plan",
            "visible_to_student": True,
        })
        hidden_followup = followup_model.with_user(self.user_admin).create({
            "student_id": self.student_cs1.id,
            "advisor_id": self.teacher_cs.id,
            "title": "Internal advisor check",
            "visible_to_student": False,
        })

        student_followups = followup_model.with_user(self.user_student1).search([])
        self.assertIn(visible_followup, student_followups)
        self.assertNotIn(hidden_followup, student_followups)

        # Student dashboard data is personal
        dashboard_data = self.env["school.dashboard"].with_user(self.user_student1).get_role_dashboard_data()
        self.assertEqual(dashboard_data["dashboard"]["user_role"], "student")
        self.assertIn("student_view", dashboard_data)
        self.assertEqual(dashboard_data["student_view"]["student"]["id"], self.student_cs1.id)

    def test_06_faculty_and_registrar_dashboard_roles(self):
        """Inherited groups must not collapse Faculty Head or Registrar dashboards."""
        faculty_data = self.env["school.dashboard"].with_user(self.user_dean).get_role_dashboard_data()
        self.assertEqual(faculty_data["dashboard"]["user_role"], "dean")
        self.assertEqual(faculty_data["faculty_view"]["faculty_name"], self.faculty_eng.name)

        registrar_data = self.env["school.dashboard"].with_user(self.user_registrar).get_role_dashboard_data()
        self.assertEqual(registrar_data["dashboard"]["user_role"], "registrar")
        self.assertIn("registrar_view", registrar_data)

    def test_06_configurable_risk_thresholds(self):
        """Changing risk thresholds in res.config.settings updates student risk calculations."""
        # Baseline: gpa 0.0, no attendances -> risk low
        self.student_cs1._compute_academic_metrics()
        self.assertEqual(self.student_cs1.risk_level, "low")

        # Admin sets threshold via ICP
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("school_management.risk_attendance_threshold", 80.0)

        from datetime import date, timedelta
        today = date.today()

        # Create low attendance for student
        self.env["university.attendance"].create({
            "student_id": self.student_cs1.id,
            "section_id": self.section_cs.id,
            "date": today - timedelta(days=1),
            "status": "absent",
        })
        self.env["university.attendance"].create({
            "student_id": self.student_cs1.id,
            "section_id": self.section_cs.id,
            "date": today - timedelta(days=2),
            "status": "absent",
        })
        self.env["university.attendance"].create({
            "student_id": self.student_cs1.id,
            "section_id": self.section_cs.id,
            "date": today - timedelta(days=3),
            "status": "absent",
        })

        self.student_cs1._compute_academic_metrics()
        self.assertEqual(self.student_cs1.attendance_rate, 0.0)
        self.assertEqual(self.student_cs1.risk_level, "medium")
        self.assertIn("Attendance is 0.0%", self.student_cs1.risk_reason)
