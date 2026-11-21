from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("-at_install", "post_install")
class TestAttendanceDashboardFeatures(TransactionCase):
    """Grid / at-risk / comparison / exports / wizard + role scope rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Attendance = cls.env["university.attendance"]
        cls.Assignment = cls.env["university.academic.assignment"]

        cls.group_teacher = cls.env.ref("school_management.group_school_teacher")
        cls.group_hod = cls.env.ref("school_management.group_school_hod")
        cls.group_dean = cls.env.ref("school_management.group_school_dean")
        cls.group_admin = cls.env.ref("school_management.group_school_admin")

        today = fields.Date.today()
        existing_year = cls.env["university.academic.year"].search([
            ("date_start", "<=", today),
            ("date_end", ">=", today),
        ], limit=1)
        if existing_year:
            cls.year = existing_year
        else:
            cls.year = cls.env["university.academic.year"].create({
                "name": "Dashboard Test Year", "date_start": f"{today.year}-01-01",
                "date_end": f"{today.year}-12-31",
            })
        existing_sem = cls.env["university.semester"].search([
            ("academic_year_id", "=", cls.year.id),
            ("semester_type", "=", "semester_1"),
        ], limit=1)
        if existing_sem:
            cls.semester = existing_sem
        else:
            cls.semester = cls.env["university.semester"].create({
                "name": "Dashboard Test Sem", "academic_year_id": cls.year.id,
                "semester_type": "semester_1",
                "date_start": cls.year.date_start, "date_end": cls.year.date_start + timedelta(days=90),
            })
        cls.faculty = cls.env["university.faculty"].create({"name": "DS Faculty", "code": "DS-FAC"})
        cls.department = cls.env["university.department"].create({
            "name": "DS Department", "code": "DS-DEP", "faculty_id": cls.faculty.id,
        })
        cls.program = cls.env["university.program"].create({
            "name": "DS Program", "code": "DS-PROG", "department_id": cls.department.id,
        })

        # Teachers: one for the main section, an outsider, a HOD, and a Dean.
        cls.teacher_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "DS Teacher", "login": "ds-attendance-teacher",
            "group_ids": [Command.set([cls.group_teacher.id])],
        })
        cls.teacher = cls.env["university.teacher"].create({
            "name": "DS Teacher", "user_id": cls.teacher_user.id,
            "faculty_id": cls.faculty.id, "department_id": cls.department.id,
        })
        cls.other_teacher_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "DS Other", "login": "ds-attendance-other",
            "group_ids": [Command.set([cls.group_teacher.id])],
        })
        cls.other_faculty = cls.env["university.faculty"].create({"name": "Other Faculty", "code": "OTH-FAC"})
        cls.other_department = cls.env["university.department"].create({
            "name": "Other Department", "code": "OTH-DEP", "faculty_id": cls.other_faculty.id,
        })
        cls.other_program = cls.env["university.program"].create({
            "name": "Other Program", "code": "OTH-PROG", "department_id": cls.other_department.id,
        })
        cls.other_teacher = cls.env["university.teacher"].create({
            "name": "DS Other", "user_id": cls.other_teacher_user.id,
            "faculty_id": cls.other_faculty.id, "department_id": cls.other_department.id,
        })

        cls.hod_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "DS HOD", "login": "ds-attendance-hod",
            "group_ids": [Command.set([cls.group_hod.id])],
        })
        cls.hod_teacher = cls.env["university.teacher"].create({
            "name": "DS HOD", "user_id": cls.hod_user.id,
            "faculty_id": cls.faculty.id, "department_id": cls.department.id,
        })

        cls.dean_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "DS Dean", "login": "ds-attendance-dean",
            "group_ids": [Command.set([cls.group_dean.id])],
        })
        cls.dean_teacher = cls.env["university.teacher"].create({
            "name": "DS Dean", "user_id": cls.dean_user.id,
            "faculty_id": cls.faculty.id, "department_id": cls.department.id,
        })

        cls.Assignment.create({
            "staff_id": cls.hod_teacher.id, "role": "department_head",
            "department_id": cls.department.id, "start_date": today - timedelta(days=30),
        })
        cls.Assignment.create({
            "staff_id": cls.dean_teacher.id, "role": "dean",
            "faculty_id": cls.faculty.id, "start_date": today - timedelta(days=30),
        })

        cls.section = cls.env["university.class.section"].create({
            "name": "DS-101", "program_id": cls.program.id,
            "semester_id": cls.semester.id, "teacher_id": cls.teacher.id,
        })
        cls.other_section = cls.env["university.class.section"].create({
            "name": "DS-102", "program_id": cls.other_program.id,
            "semester_id": cls.semester.id, "teacher_id": cls.other_teacher.id,
        })

        cls.student_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "DS Student", "login": "ds-attendance-student",
            "group_ids": [Command.set([cls.env.ref("school_management.group_school_student").id])],
        })
        cls.student = cls.env["university.student"].create({
            "name": "DS Student", "user_id": cls.student_user.id,
            "program_id": cls.program.id, "department_id": cls.department.id,
        })
        cls.second_student = cls.env["university.student"].create({
            "name": "DS Second", "program_id": cls.program.id,
            "department_id": cls.department.id,
        })
        cls.env["university.enrollment"].create({
            "student_id": cls.student.id, "program_id": cls.program.id,
            "section_id": cls.section.id, "semester_id": cls.semester.id,
            "academic_year_id": cls.year.id, "status": "enrolled",
        })
        cls.env["university.enrollment"].create({
            "student_id": cls.second_student.id, "program_id": cls.program.id,
            "section_id": cls.section.id, "semester_id": cls.semester.id,
            "academic_year_id": cls.year.id, "status": "enrolled",
        })
        cls.env["university.enrollment"].create({
            "student_id": cls.student.id, "program_id": cls.other_program.id,
            "section_id": cls.other_section.id, "semester_id": cls.semester.id,
            "academic_year_id": cls.year.id, "status": "enrolled",
        })

        cls.old_date = today - timedelta(days=6)
        cls.att = cls.Attendance.create({
            "student_id": cls.student.id, "section_id": cls.section.id,
            "date": cls.old_date, "status": "absent", "remark": "Sick",
        })

    def _grid(self, user=None, section_ids=None, month=None, year=None):
        model = self.Attendance.with_user(user or self.env.user)
        return model.get_grid_data(
            section_ids or [], month or self.old_date.month, year or self.old_date.year
        )

    def test_attendance_percentage_credits_present_late_and_excused(self):
        self.assertEqual(self.Attendance._attendance_percentage(
            {"present": 6, "absent": 1, "late": 1, "excused": 2}), 90.0)

    def test_teacher_grid_scoped_to_own_sections_with_day_cells(self):
        grid = self._grid(self.teacher_user)
        sections = {s["id"]: s for s in grid["sections"]}
        self.assertIn(self.section.id, sections)
        self.assertNotIn(self.other_section.id, sections)
        section = sections[self.section.id]
        self.assertEqual(len(section["students"]), 2)
        by_id = {s["student_id"]: s for s in section["students"]}
        row = by_id[self.student.id]
        recorded = [c for c in row["cells"] if c["status"]]
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["status"], "absent")
        self.assertEqual(recorded[0]["code"], "A")
        self.assertTrue(grid["can_edit"])

    def test_hod_and_dean_read_only_grid_with_scope(self):
        hod_grid = self._grid(self.hod_user, section_ids=[self.section.id, self.other_section.id])
        self.assertTrue(all(s["id"] == self.section.id for s in hod_grid["sections"]))
        self.assertFalse(hod_grid["can_edit"])
        dean_grid = self._grid(self.dean_user)
        self.assertTrue(all(s["id"] == self.section.id for s in dean_grid["sections"]))
        other_grid = self._grid(self.other_teacher_user)
        self.assertTrue(all(s["id"] == self.other_section.id for s in other_grid["sections"]))

    def test_hod_and_dean_cannot_write_attendance(self):
        with self.assertRaises(AccessError):
            self.att.with_user(self.hod_user).write({"remark": "nope"})
        with self.assertRaises(AccessError):
            self.att.with_user(self.dean_user).write({"status": "present"})

    def test_update_cell_by_own_teacher(self):
        result = self.Attendance.with_user(self.teacher_user).update_cell(
            self.section.id, self.student.id,
            fields.Date.to_string(self.old_date), "excused", "Exam day"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "excused")
        self.assertEqual(result["code"], "E")
        self.assertEqual(self.att.remark, "Exam day")

    def test_update_cell_rejected_for_outsider_and_future_and_closed_window(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "school_management.attendance_edit_window_days", 3)
        self.addCleanup(
            self.env["ir.config_parameter"].sudo().set_param,
            "school_management.attendance_edit_window_days", 7)
        with self.assertRaises(AccessError):
            self.Attendance.with_user(self.other_teacher_user).update_cell(
                self.section.id, self.student.id,
                fields.Date.to_string(self.old_date), "present")
        future = fields.Date.today() + timedelta(days=1)
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(ValidationError):
                self.Attendance.with_user(self.teacher_user).update_cell(
                    self.section.id, self.student.id,
                    fields.Date.to_string(future), "present")
        closed = fields.Date.today() - timedelta(days=5)
        with self.assertRaises(ValidationError):
            self.Attendance.with_user(self.teacher_user).update_cell(
                self.section.id, self.student.id,
                fields.Date.to_string(closed), "present")

    def test_at_risk_flags_below_threshold_with_excused_credited(self):
        today = fields.Date.today()
        self.env["ir.config_parameter"].sudo().set_param(
            "school_management.risk_attendance_threshold", 80.0)
        self.addCleanup(
            self.env["ir.config_parameter"].sudo().set_param,
            "school_management.risk_attendance_threshold", 75.0)
        self.Attendance.create([
            {"student_id": self.student.id, "section_id": self.section.id,
             "date": today - timedelta(days=i), "status": status}
            for i, status in enumerate(["present", "absent", "excused", "late"], start=1)
        ])
        data = self.Attendance.with_user(self.teacher_user).get_at_risk_data(
            today.month, today.year, [self.section.id])
        self.assertEqual(data["threshold"], 80.0)
        flagged = [s for s in data["students"] if s["id"] == self.student.id]
        # old absent + present + absent + excused + late = 5 records, 3 credited.
        self.assertTrue(flagged)
        self.assertEqual(flagged[0]["rate"], 60.0)

    def test_comparison_rollup(self):
        data = self.Attendance.with_user(self.teacher_user).get_comparison_data()
        departments = {d["id"]: d for d in data["departments"]}
        self.assertIn(self.department.id, departments)
        dept = departments[self.department.id]
        self.assertEqual(dept["total"], 1)
        self.assertEqual(dept["rate"], 0.0)

    def test_student_dashboard(self):
        payload = self.Attendance.with_user(self.student_user).get_student_dashboard(
            self.old_date.month, self.old_date.year)
        self.assertEqual(payload["student"]["id"], self.student.id)
        self.assertEqual(payload["summary"]["absent"], 1)
        self.assertEqual(payload["rate"], 0.0)
        self.assertIn("calendar", payload)
        self.assertEqual(len(payload["records"]), 1)

    def test_exports_produce_filable_bytes(self):
        xlsx = self.Attendance.build_grid_xlsx(
            self.old_date.month, self.old_date.year, [self.section.id])
        self.assertTrue(xlsx.startswith(b"PK"))
        csv_bytes = self.Attendance.build_grid_csv(
            self.old_date.month, self.old_date.year, [self.section.id])
        self.assertIn(b"DS Student", csv_bytes)
        at_risk = self.Attendance.build_at_risk_csv(
            self.old_date.month, self.old_date.year, [self.section.id])
        self.assertTrue(at_risk.startswith(b"At-Risk") or b"Threshold" in at_risk[:100])

    def test_take_wizard_loads_students_and_saves(self):
        wizard = self.env["university.attendance.take.wizard"].with_user(
            self.teacher_user).create({
                "section_id": self.section.id,
                "date": fields.Date.to_string(self.old_date),
            })
        self.assertEqual(len(wizard.line_ids), 2)
        wizard.action_mark_all_present()
        self.assertTrue(all(line.status == "present" for line in wizard.line_ids))
        wizard.action_save()
        records = self.Attendance.search([
            ("section_id", "=", self.section.id), ("date", "=", self.old_date),
        ])
        self.assertEqual(len(records), 2)
        self.assertTrue(all(r.status == "present" for r in records))

    def test_take_wizard_default_get_preloads_lines(self):
        defaults = self.env["university.attendance.take.wizard"].with_user(
            self.teacher_user).with_context(
                default_section_id=self.section.id,
                default_date=fields.Date.to_string(self.old_date),
            ).default_get(["section_id", "date", "notes", "line_ids"])
        self.assertEqual(defaults.get("section_id"), self.section.id)
        self.assertEqual(len(defaults.get("line_ids", [])), 2)

    def test_print_wizard_grid_data_and_actions_exist(self):
        wizard = self.env["university.attendance.print.wizard"].create({
            "month": str(self.old_date.month), "year": self.old_date.year,
            "section_ids": [Command.set([self.section.id])],
        })
        grid = wizard.get_grid_data()
        self.assertTrue(grid["sections"])
        by_id = {s["student_id"]: s for s in grid["sections"][0]["students"]}
        self.assertEqual(by_id[self.student.id]["counts"]["absent"], 1)
        self.assertTrue(hasattr(wizard, "action_print_pdf"))
        self.assertTrue(hasattr(wizard, "action_export_xlsx"))
        self.assertTrue(hasattr(wizard, "action_export_csv"))
        self.assertTrue(hasattr(wizard, "action_export_at_risk_csv"))

    def test_comparison_cross_department_teacher_access(self):
        self.other_section.write({"teacher_id": self.teacher.id})
        data = self.Attendance.with_user(self.teacher_user).get_comparison_data()
        departments = {d["id"]: d for d in data["departments"]}
        self.assertIn(self.department.id, departments)
        self.assertIn(self.other_department.id, departments)

    def test_comparison_hod_cross_department_teaching(self):
        self.other_section.write({"teacher_id": self.hod_teacher.id})
        data = self.Attendance.with_user(self.hod_user).get_comparison_data()
        departments = {d["id"]: d for d in data["departments"]}
        self.assertIn(self.department.id, departments)
        self.assertIn(self.other_department.id, departments)

    def test_course_section_subject_department_grouping(self):
        subject = self.env["university.subject"].create({
            "name": "Course Subject",
            "code": "CS-101",
            "department_id": self.other_department.id,
            "credits": 3,
        })
        course_section = self.env["university.class.section"].create({
            "name": "CS-SEC",
            "section_type": "course",
            "subject_id": subject.id,
            "semester_id": self.semester.id,
            "teacher_id": self.teacher.id,
        })
        self.assertFalse(course_section.department_id)
        data = self.Attendance.with_user(self.teacher_user).get_comparison_data()
        departments = {d["id"]: d for d in data["departments"]}
        self.assertIn(self.other_department.id, departments)
        dept_data = departments[self.other_department.id]
        section_ids = [s["id"] for s in dept_data["sections"]]
        self.assertIn(course_section.id, section_ids)

    def test_at_risk_hod_cross_department_student_access(self):
        # Student from another department enrolled in HOD's department section
        outsider_student = self.env["university.student"].create({
            "name": "Outsider Student",
            "program_id": self.other_program.id,
            "department_id": self.other_department.id,
        })
        self.env["university.enrollment"].create({
            "student_id": outsider_student.id,
            "program_id": self.program.id,
            "section_id": self.section.id,
            "semester_id": self.semester.id,
            "academic_year_id": self.year.id,
            "status": "enrolled",
        })
        today = fields.Date.today()
        self.Attendance.create({
            "student_id": outsider_student.id,
            "section_id": self.section.id,
            "date": today,
            "status": "absent",
        })
        data = self.Attendance.with_user(self.hod_user).get_at_risk_data(
            today.month, today.year, [self.section.id]
        )
        student_ids = [s["id"] for s in data["students"]]
        self.assertIn(outsider_student.id, student_ids)

    def test_at_risk_dean_cross_faculty_student_access(self):
        outsider_student = self.env["university.student"].create({
            "name": "Outsider Faculty Student",
            "program_id": self.other_program.id,
            "department_id": self.other_department.id,
        })
        self.env["university.enrollment"].create({
            "student_id": outsider_student.id,
            "program_id": self.program.id,
            "section_id": self.section.id,
            "semester_id": self.semester.id,
            "academic_year_id": self.year.id,
            "status": "enrolled",
        })
        today = fields.Date.today()
        self.Attendance.create({
            "student_id": outsider_student.id,
            "section_id": self.section.id,
            "date": today,
            "status": "absent",
        })
        data = self.Attendance.with_user(self.dean_user).get_at_risk_data(
            today.month, today.year, [self.section.id]
        )
        student_ids = [s["id"] for s in data["students"]]
        self.assertIn(outsider_student.id, student_ids)
