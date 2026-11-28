from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestStaffAttendance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.faculty = cls.env["university.faculty"].create({
            "name": "Faculty of Attendance Engineering",
            "code": "FAE",
        })
        cls.department = cls.env["university.department"].create({
            "name": "Department of Staff Attendance",
            "code": "DSA",
            "faculty_id": cls.faculty.id,
        })
        cls.teacher_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Prof Staff Test",
            "login": "prof_staff_test@university.edu",
            "email": "prof_staff_test@university.edu",
            "group_ids": [(6, 0, [cls.env.ref("school_management.group_school_teacher").id])],
        })
        cls.teacher = cls.env["university.teacher"].create({
            "name": "Prof Staff Test",
            "department_id": cls.department.id,
            "user_id": cls.teacher_user.id,
            "email": "prof_staff_test@university.edu",
        })
        cls.other_teacher_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Dr Other Test",
            "login": "dr_other_test@university.edu",
            "email": "dr_other_test@university.edu",
            "group_ids": [(6, 0, [cls.env.ref("school_management.group_school_teacher").id])],
        })
        cls.other_teacher = cls.env["university.teacher"].create({
            "name": "Dr Other Test",
            "department_id": cls.department.id,
            "user_id": cls.other_teacher_user.id,
            "email": "dr_other_test@university.edu",
        })

    def test_worked_hours_calculation(self):
        att = self.env["university.staff.attendance"].create({
            "staff_id": self.teacher.id,
            "date": "2026-10-15",
            "check_in": "2026-10-15 08:00:00",
            "check_out": "2026-10-15 16:30:00",
            "status": "present",
        })
        self.assertAlmostEqual(att.worked_hours, 8.5, places=2)

    def test_check_out_must_be_after_check_in(self):
        with self.assertRaises(ValidationError):
            self.env["university.staff.attendance"].create({
                "staff_id": self.teacher.id,
                "date": "2026-10-16",
                "check_in": "2026-10-16 17:00:00",
                "check_out": "2026-10-16 08:00:00",
                "status": "present",
            })

    def test_unique_staff_date_constraint(self):
        self.env["university.staff.attendance"].create({
            "staff_id": self.teacher.id,
            "date": "2026-10-17",
            "status": "present",
        })
        with self.assertRaises(Exception):
            self.env["university.staff.attendance"].create({
                "staff_id": self.teacher.id,
                "date": "2026-10-17",
                "status": "late",
            })

    def test_attendance_workflow_states(self):
        att = self.env["university.staff.attendance"].create({
            "staff_id": self.teacher.id,
            "date": "2026-10-18",
            "status": "present",
            "state": "draft",
        })
        self.assertEqual(att.state, "draft")
        # Draft -> Submitted
        att.action_submit()
        self.assertEqual(att.state, "submitted")
        # Submitted -> Approved
        att.action_approve()
        self.assertEqual(att.state, "approved")
        # Approved -> Draft
        att.action_reset_draft()
        self.assertEqual(att.state, "draft")

        # Draft -> Submitted -> Rejected -> Draft
        att.action_submit()
        self.assertEqual(att.state, "submitted")
        att.action_reject()
        self.assertEqual(att.state, "rejected")
        att.action_reset_draft()
        self.assertEqual(att.state, "draft")

    def test_attendance_invalid_transitions(self):
        att = self.env["university.staff.attendance"].create({
            "staff_id": self.teacher.id,
            "date": "2026-10-19",
            "status": "present",
            "state": "draft",
        })
        # From draft, cannot directly approve, reject, or reset
        with self.assertRaises(ValidationError):
            att.action_approve()
        with self.assertRaises(ValidationError):
            att.action_reject()
        with self.assertRaises(ValidationError):
            att.action_reset_draft()

        # From draft, direct write of approved must fail
        with self.assertRaises(ValidationError):
            att.write({"state": "approved"})

        # Submit to move to submitted
        att.action_submit()
        # From submitted, cannot re-submit
        with self.assertRaises(ValidationError):
            att.action_submit()

        att.action_approve()
        # From approved, cannot approve again or reject directly
        with self.assertRaises(ValidationError):
            att.action_approve()
        with self.assertRaises(ValidationError):
            att.action_reject()

    def test_attendance_security_permissions(self):
        # Teacher user cannot create pre-approved records
        with self.assertRaises(AccessError):
            self.env["university.staff.attendance"].with_user(self.teacher_user).create({
                "staff_id": self.teacher.id,
                "date": "2026-10-21",
                "status": "present",
                "state": "approved",
            })

        # Teacher user creates draft record for self
        att = self.env["university.staff.attendance"].with_user(self.teacher_user).create({
            "staff_id": self.teacher.id,
            "date": "2026-10-22",
            "status": "present",
        })
        self.assertEqual(att.state, "draft")

        # Teacher can submit own record
        att.with_user(self.teacher_user).action_submit()
        self.assertEqual(att.state, "submitted")

        # Teacher CANNOT approve or reject
        with self.assertRaises(AccessError):
            att.with_user(self.teacher_user).action_approve()
        with self.assertRaises(AccessError):
            att.with_user(self.teacher_user).action_reject()

        # Teacher CANNOT submit someone else's record
        other_att = self.env["university.staff.attendance"].create({
            "staff_id": self.other_teacher.id,
            "date": "2026-10-22",
            "status": "present",
            "state": "draft",
        })
        with self.assertRaises(AccessError):
            other_att.with_user(self.teacher_user).action_submit()

    def test_attendance_approved_record_locking(self):
        att = self.env["university.staff.attendance"].create({
            "staff_id": self.teacher.id,
            "date": "2026-10-23",
            "status": "present",
            "check_in": "2026-10-23 08:00:00",
            "check_out": "2026-10-23 17:00:00",
        })
        att.action_submit()
        att.action_approve()
        self.assertEqual(att.state, "approved")

        # Modifying attendance data on approved record raises UserError
        with self.assertRaises(UserError):
            att.write({"status": "late"})
        with self.assertRaises(UserError):
            att.write({"remark": "Modified remark"})

        # Once reset to draft by admin, modification is allowed
        att.action_reset_draft()
        self.assertEqual(att.state, "draft")
        att.write({"status": "late", "remark": "Modified in draft"})
        self.assertEqual(att.status, "late")

    def test_new_statuses_affect_teacher_presence(self):
        today = date.today()
        # Official duty counts as present
        att = self.env["university.staff.attendance"].create({
            "staff_id": self.teacher.id,
            "date": today,
            "status": "official_duty",
        })
        self.teacher._compute_presence()
        self.assertTrue(self.teacher.is_present)
        self.assertFalse(self.teacher.on_leave)

        # Half day counts as present
        att.write({"status": "half_day"})
        self.teacher._compute_presence()
        self.assertTrue(self.teacher.is_present)

        # On leave counts as on_leave
        att.write({"status": "leave"})
        self.teacher._compute_presence()
        self.assertFalse(self.teacher.is_present)
        self.assertTrue(self.teacher.on_leave)

    def test_holiday_detection(self):
        year = self.env["university.academic.year"].create({
            "name": "Holiday Test Year",
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
        })
        holiday = self.env["university.holiday"].create({
            "name": "Mid-Autumn Festival",
            "date_start": "2026-10-20",
            "date_end": "2026-10-20",
            "academic_year_id": year.id,
        })
        att = self.env["university.staff.attendance"].create({
            "staff_id": self.teacher.id,
            "date": "2026-10-20",
            "status": "present",
        })
        self.assertTrue(att.is_holiday)
        self.assertEqual(att.holiday_name, "Mid-Autumn Festival")

    def test_res_config_settings_attendance_parameters(self):
        settings = self.env["res.config.settings"].create({
            "staff_expected_check_in": 8.5,
            "staff_expected_check_out": 17.5,
            "staff_late_grace_minutes": 20,
        })
        settings.set_values()
        ICP = self.env["ir.config_parameter"].sudo()
        self.assertEqual(ICP.get_param("school_management.staff_expected_check_in"), "8.5")
        self.assertEqual(ICP.get_param("school_management.staff_expected_check_out"), "17.5")
        self.assertEqual(ICP.get_param("school_management.staff_late_grace_minutes"), "20")
