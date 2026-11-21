import json
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import ChromeBrowser, HttpCase, TransactionCase
from odoo.tests import tagged


class _AttendanceSheetFixtures:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Attendance = cls.env["university.attendance"]
        cls.Session = cls.env["university.attendance.session"]
        existing_year = cls.env["university.academic.year"].search([
            ("date_start", "<=", "2026-09-30"),
            ("date_end", ">=", "2026-09-30"),
        ], limit=1)
        cls.year = existing_year or cls.env["university.academic.year"].create({
            "name": "Attendance Test Year", "date_start": "2026-01-01", "date_end": "2026-12-31",
        })
        existing_sem = cls.env["university.semester"].search([
            ("academic_year_id", "=", cls.year.id),
            ("semester_type", "=", "semester_1"),
        ], limit=1)
        cls.semester = existing_sem or cls.env["university.semester"].create({
            "name": "Attendance Test Semester", "academic_year_id": cls.year.id,
            "semester_type": "semester_1", "date_start": cls.year.date_start, "date_end": cls.year.date_end,
        })
        faculty = cls.env["university.faculty"].create({"name": "Attendance Faculty", "code": "AT-FAC"})
        department = cls.env["university.department"].create({
            "name": "Attendance Department", "code": "AT-DEP", "faculty_id": faculty.id,
        })
        cls.program = cls.env["university.program"].create({
            "name": "Attendance Major", "code": "AT-MAJ", "department_id": department.id,
        })
        cls.teacher_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Attendance Teacher", "login": "attendance-sheet-teacher",
            "group_ids": [Command.set([cls.env.ref("school_management.group_school_teacher").id])],
        })
        teacher = cls.env["university.teacher"].create({
            "name": "Attendance Teacher", "user_id": cls.teacher_user.id, "department_id": department.id,
        })
        cls.section = cls.env["university.class.section"].create({
            "name": "AT-202", "program_id": cls.program.id,
            "semester_id": cls.semester.id, "teacher_id": teacher.id,
        })
        cls.student = cls.env["university.student"].create({
            "name": "Attendance Student", "program_id": cls.program.id,
        })
        cls.env["university.enrollment"].create({
            "student_id": cls.student.id, "program_id": cls.program.id, "section_id": cls.section.id,
            "semester_id": cls.semester.id, "academic_year_id": cls.year.id, "status": "enrolled",
        })
        cls.student_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Attendance Student Login", "login": "attendance-sheet-student",
            "group_ids": [Command.set([cls.env.ref("school_management.group_school_student").id])],
        })


@tagged("-at_install", "post_install")
class TestAttendanceSheet(_AttendanceSheetFixtures, TransactionCase):
    def _save(self, status="present", date="2026-09-30", remark="", notes="Session note"):
        return self.Attendance.save_sheet(self.section.id, date, [{
            "student_id": self.student.id, "status": status, "remark": remark,
        }], notes)

    def test_loading_is_read_only_and_returns_session_metadata(self):
        count = self.Session.search_count([])
        sheet = self.Attendance.get_sheet(self.section.id, "2026-09-30")
        self.assertFalse(sheet["session_id"])
        self.assertEqual(self.Session.search_count([]), count)
        self.assertEqual(sheet["teacher"], "Attendance Teacher")
        self.assertEqual(sheet["semester"], self.semester.display_name)
        self.assertEqual(sheet["academic_year"], self.year.display_name)

    def test_save_preserves_attendance_and_records_real_chatter(self):
        sheet = self._save()
        session = self.Session.browse(sheet["session_id"])
        self.assertEqual(session.state, "recorded")
        self.assertEqual(session.notes, "Session note")
        self.assertEqual(session.recorded_by_id, self.env.user)
        self.assertTrue(session.recorded_at)
        self.assertTrue(any("Attendance recorded" in message.body for message in session.message_ids))
        updated = self._save(status="excused", remark="Excused", notes="Updated session note")
        self.assertEqual(updated["session_id"], session.id)
        self.assertEqual(updated["lines"][0]["status"], "excused")
        self.assertEqual(updated["lines"][0]["remark"], "Excused")
        self.assertEqual(updated["notes"], "Updated session note")
        self.assertTrue(any("Present -&gt; Excused" in message.body for message in session.message_ids))

    def test_sessions_are_isolated_by_date(self):
        first = self._save()
        second = self._save(date="2026-10-01", status="absent", notes="Other day")
        self.assertNotEqual(first["session_id"], second["session_id"])
        self.assertEqual(self.Attendance.get_sheet(self.section.id, "2026-09-30")["notes"], "Session note")

    def test_invalid_lines_and_notes_do_not_create_session(self):
        with self.assertRaises(ValidationError):
            self._save(status="invalid")
        with self.assertRaises(ValidationError):
            self.Attendance.save_sheet(self.section.id, "2026-09-30", [], notes={})
        self.assertFalse(self.Session.search([("section_id", "=", self.section.id)]))

    def test_teacher_can_save_and_student_cannot_access_session_thread(self):
        today_str = str(fields.Date.today())
        sheet = self.Attendance.with_user(self.teacher_user).save_sheet(
            self.section.id, today_str, [{"student_id": self.student.id, "status": "late"}], "Teacher note",
        )
        session = self.Session.browse(sheet["session_id"])
        self.assertEqual(session.recorded_by_id, self.teacher_user)
        self.assertEqual(session.with_user(self.teacher_user).notes, "Teacher note")
        with self.assertRaises(AccessError):
            session.with_user(self.student_user).read(["notes"])
        with self.assertRaises(AccessError):
            self.Attendance.with_user(self.student_user).get_sheet(self.section.id, today_str)

    def test_other_teacher_cannot_read_or_edit_session(self):
        sheet = self._save()
        outsider = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Other Attendance Teacher", "login": "attendance-sheet-outsider",
            "group_ids": [Command.set([self.env.ref("school_management.group_school_teacher").id])],
        })
        session = self.Session.browse(sheet["session_id"]).with_user(outsider)
        with self.assertRaises(AccessError):
            session.read(["notes"])
        with self.assertRaises(AccessError):
            session.write({"notes": "Unauthorized change"})

    def test_university_is_single_entry_point(self):
        root = self.env.ref("school_management.menu_school_root")
        for user in (self.teacher_user, self.student_user, self.env.user):
            visible_roots = self.env["ir.ui.menu"].with_user(user).get_user_roots()
            self.assertIn(root, visible_roots)
            self.assertNotIn("Student Portal", visible_roots.mapped("name"))
        self.assertFalse(self.env["ir.model.data"].search([
            ("module", "=", "school_management"), ("model", "=", "ir.ui.menu"),
            ("name", "=like", "menu_school_student_portal_%"),
        ]))


@tagged("-at_install", "post_install")
class TestAttendanceSheetBrowser(_AttendanceSheetFixtures, HttpCase):
    def _check_sheet(self, width):
        self.browser_size = f"{width}x1000"
        self.Attendance.save_sheet(self.section.id, "2026-09-30", [{
            "student_id": self.student.id, "status": "present",
        }], "Browser session note")
        code = """
            (async () => {
                const assert = (condition, message) => { if (!condition) throw new Error(message); };
                const waitFor = async (check) => {
                    for (let i = 0; i < 200; i++) {
                        if (check()) return;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error('Attendance screen did not finish rendering');
                };
                await odoo.__WOWL_DEBUG__.root.env.services.action.doAction({
                    type: 'ir.actions.client', name: 'Track Attendance', tag: 'university_attendance_sheet',
                    context: {default_section_id: SECTION_ID, default_date: '2026-09-30'},
                });
                await waitFor(() => document.querySelector('.o_att_student_name'));
                const sheet = document.querySelector('.o_att_sheet');
                assert(sheet.querySelector('.o_att_breadcrumb_record').textContent.includes('AT-202'), 'Missing section breadcrumb');
                assert(sheet.querySelectorAll('.att_container').length >= 4, 'Missing attendance statistics');
                assert(getComputedStyle(sheet).backgroundColor === 'rgb(255, 255, 255)', 'Attendance background is not light');
                await waitFor(() => sheet.querySelector('.o-mail-Chatter-sendMessage'));
                assert(sheet.querySelector('.o-mail-Chatter-logNote'), 'Missing standard log note button');
                assert(sheet.querySelector('.o-mail-Chatter-activity'), 'Missing standard activity button');
                const chatterBar = sheet.querySelector('.o-mail-Chatter-topbar');
                assert(chatterBar.scrollWidth <= chatterBar.clientWidth + 1, 'Chatter toolbar overflows');
                const row = sheet.querySelector('.o_att_row');
                row.querySelector('[data-status="excused"]').click();
                sheet.querySelector('[data-filter="excused"]').click();
                await waitFor(() => sheet.querySelector('[data-status="excused"][aria-checked="true"]'));
                assert(sheet.querySelectorAll('.o_att_student_name').length === 1, 'Excused filter lost the excused student');
                sheet.querySelector('[data-tab="details"]').click();
                await waitFor(() => sheet.querySelector('#att_session_notes'));
                const notes = sheet.querySelector('#att_session_notes');
                assert(notes.value === 'Browser session note', 'Session notes were not loaded');
                notes.value = 'Saved browser note';
                notes.dispatchEvent(new Event('input', {bubbles: true}));
                sheet.querySelector('.o_att_btn--primary').click();
                await waitFor(() => sheet.querySelector('.o_att_hint').textContent.includes('All changes saved'));
                sheet.querySelector('[data-tab="attendance"]').click();
                await waitFor(() => sheet.querySelector('[data-filter="all"]'));
                sheet.querySelector('[data-filter="all"]').click();
                await waitFor(() => sheet.querySelector('.o_att_student_name'));
                const seg = sheet.querySelector('.o_att_seg');
                assert(seg.scrollWidth <= seg.clientWidth + 1, 'Attendance controls overflow');
                assert(sheet.scrollWidth <= sheet.clientWidth + 1, 'Attendance page overflows horizontally');
                const left = sheet.querySelector('.o_att_shell').getBoundingClientRect();
                const chatter = sheet.querySelector('.o_att_chatter').getBoundingClientRect();
                if (window.innerWidth >= 1180) assert(chatter.left >= left.right - 1, 'Chatter overlaps the attendance form');
                else assert(chatter.top >= left.bottom - 1, 'Mobile chatter overlaps the attendance form');
                console.log('test successful');
            })().catch(error => console.error(error));
        """.replace("SECTION_ID", json.dumps(self.section.id))
        original = ChromeBrowser._wait_code_ok

        def capture(browser, *args, **kwargs):
            result = original(browser, *args, **kwargs)
            browser.take_screenshot(prefix=f"attendance_{width}_").result(timeout=10)
            return result

        with patch.object(ChromeBrowser, "_wait_code_ok", capture):
            self.browser_js("/odoo?debug=1", code, ready="odoo.isReady === true", login="admin", timeout=90)
        self.env.invalidate_all()
        saved = self.Attendance.get_sheet(self.section.id, "2026-09-30")
        self.assertEqual(saved["notes"], "Saved browser note")
        self.assertEqual(saved["lines"][0]["status"], "excused")

    def test_desktop_attendance_layout_and_controls(self):
        self._check_sheet(1440)

    def test_mobile_attendance_layout_and_controls(self):
        self._check_sheet(390)
