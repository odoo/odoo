import base64
from datetime import date, datetime
import io

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged

try:
    import openpyxl
except ImportError:
    openpyxl = None


@tagged("post_install", "-at_install", "school_public_holiday")
class TestPublicHolidayManagement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Holiday = cls.env["university.holiday"]
        cls.PublicHoliday = cls.env["public.holiday"]
        cls.Slot = cls.env["university.timetable.slot"]
        cls.Section = cls.env["university.class.section"]
        cls.Faculty = cls.env["university.faculty"]
        cls.Department = cls.env["university.department"]
        cls.Program = cls.env["university.program"]
        cls.AcademicYear = cls.env["university.academic.year"]

        cls.admin_user = cls.env.ref("base.user_admin")
        cls.teacher_user = cls.env["res.users"].search([("login", "=", "teacher")], limit=1)
        if not cls.teacher_user:
            cls.teacher_user = cls.env["res.users"].search([("teacher_id", "!=", False)], limit=1)
        if not cls.teacher_user:
            cls.teacher_user = cls.env["res.users"].create({
                "name": "Teacher User",
                "login": "teacher_test_user",
                "email": "teacher_test@example.com",
            })
        cls.teacher_user.write({
            "group_ids": [
                Command.link(cls.env.ref("base.group_user").id),
                Command.link(cls.env.ref("school_management.group_school_teacher").id),
                Command.unlink(cls.env.ref("school_management.group_school_admin").id),
                Command.unlink(cls.env.ref("base.group_system").id),
            ]
        })

        # Base Academic Year
        cls.ay = cls.AcademicYear.search([], limit=1)
        if not cls.ay:
            cls.ay = cls.AcademicYear.create({
                "name": "2026-2027 Test Year",
                "date_start": "2026-01-01",
                "date_end": "2026-12-31",
            })
        else:
            try:
                cls.ay.write({
                    "date_start": min(cls.ay.date_start, date(2026, 1, 1)),
                    "date_end": max(cls.ay.date_end, date(2026, 12, 31)),
                })
            except Exception:
                pass

        cls.semester = cls.env["university.semester"].search([("academic_year_id", "=", cls.ay.id)], limit=1)
        if not cls.semester:
            cls.semester = cls.env["university.semester"].create({
                "name": "Test Semester",
                "academic_year_id": cls.ay.id,
                "date_start": "2026-01-01",
                "date_end": "2026-12-31",
            })
        else:
            try:
                cls.semester.write({
                    "date_start": date(2026, 1, 1),
                    "date_end": date(2026, 12, 31),
                })
            except Exception:
                pass

        # Faculties & Sections
        cls.faculty_a = cls.Faculty.search([("name", "=", "Faculty A Test")], limit=1)
        if not cls.faculty_a:
            cls.faculty_a = cls.Faculty.create({"name": "Faculty A Test", "code": "FA_TEST"})

        cls.faculty_b = cls.Faculty.search([("name", "=", "Faculty B Test")], limit=1)
        if not cls.faculty_b:
            cls.faculty_b = cls.Faculty.create({"name": "Faculty B Test", "code": "FB_TEST"})

        cls.dept_a = cls.Department.create({"name": "Dept标志 A", "code": "DA", "faculty_id": cls.faculty_a.id})
        cls.prog_a = cls.Program.create({"name": "Prog A", "code": "PRG_A", "department_id": cls.dept_a.id})

        cls.dept_b = cls.Department.create({"name": "Dept B", "code": "DB", "faculty_id": cls.faculty_b.id})
        cls.prog_b = cls.Program.create({"name": "Prog B", "code": "PRG_B", "department_id": cls.dept_b.id})

        cls.teacher = cls.env["university.teacher"].search([], limit=1)
        if not cls.teacher:
            cls.teacher = cls.env["university.teacher"].create({"name": "Test Instructor"})

        cls.subject = cls.env["university.subject"].create({
            "name": "Test Subject Holiday",
            "code": "TSH_TEST",
            "program_ids": [(6, 0, [cls.prog_a.id, cls.prog_b.id])],
            "teacher_ids": [(6, 0, [cls.teacher.id])],
        })

        cls.section_a = cls.Section.create({
            "name": "Sec A Test",
            "semester_id": cls.semester.id,
            "program_id": cls.prog_a.id,
            "department_id": cls.dept_a.id,
            "subject_id": cls.subject.id,
            "teacher_id": cls.teacher.id,
        })
        cls.section_b = cls.Section.create({
            "name": "Sec B Test",
            "semester_id": cls.semester.id,
            "program_id": cls.prog_b.id,
            "department_id": cls.dept_b.id,
            "subject_id": cls.subject.id,
            "teacher_id": cls.teacher.id,
        })

    def test_01_overlap_constraint_same_and_different_scope(self):
        """Test overlapping holidays with same scope are rejected, different scopes allowed."""
        h1 = self.Holiday.create({
            "name": "Faculty A Holiday",
            "date_from": "2026-07-10",
            "date_to": "2026-07-12",
            "applies_to": "faculty",
            "faculty_ids": [(6, 0, [self.faculty_a.id])],
            "academic_year_id": self.ay.id,
        })
        self.assertTrue(h1.id)

        with self.assertRaises(ValidationError):
            self.Holiday.create({
                "name": "Faculty A Holiday Clash",
                "date_from": "2026-07-11",
                "date_to": "2026-07-15",
                "applies_to": "faculty",
                "faculty_ids": [(6, 0, [self.faculty_a.id])],
                "academic_year_id": self.ay.id,
            })

        h2 = self.Holiday.create({
            "name": "Faculty B Holiday Same Dates",
            "date_from": "2026-07-10",
            "date_to": "2026-07-12",
            "applies_to": "faculty",
            "faculty_ids": [(6, 0, [self.faculty_b.id])],
            "academic_year_id": self.ay.id,
        })
        self.assertTrue(h2.id)

        with self.assertRaises(ValidationError):
            self.Holiday.create({
                "name": "All University Holiday Clash",
                "date_from": "2026-07-11",
                "date_to": "2026-07-11",
                "applies_to": "all",
                "academic_year_id": self.ay.id,
            })

    def test_02_applies_to_scoping_helpers(self):
        """Test is_holiday and get_holiday_dates respecting section hierarchy."""
        h = self.Holiday.create({
            "name": "Special Engineering Day",
            "date_from": "2026-08-05",
            "date_to": "2026-08-06",
            "applies_to": "faculty",
            "faculty_ids": [(6, 0, [self.faculty_a.id])],
            "academic_year_id": self.ay.id,
        })

        target_date = date(2026, 8, 5)
        self.assertTrue(self.Holiday.is_holiday(target_date))
        self.assertTrue(self.Holiday.is_holiday(target_date, section=self.section_a))
        self.assertFalse(self.Holiday.is_holiday(target_date, section=self.section_b))

        dates_a = self.Holiday.get_holiday_dates("2026-08-01", "2026-08-10", section=self.section_a)
        self.assertEqual(dates_a, {date(2026, 8, 5), date(2026, 8, 6)})

        dates_b = self.Holiday.get_holiday_dates("2026-08-01", "2026-08-10", section=self.section_b)
        self.assertEqual(dates_b, set())

    def test_03_csv_import_valid_and_duplicate_policies(self):
        """Test CSV file import with skip and update duplicate policies."""
        csv_data = (
            "Name,Date From,Date To,Holiday Type,Work Pay Multiplier,Note\n"
            "Midyear Festival,2026-06-10,2026-06-12,public,2.0,Midyear festival\n"
            "Sea Festival,2026-12-11,2026-12-13,public,2.0,Coastal celebration\n"
        )
        wizard = self.env["wizard.import.public.holiday"].create({
            "file_data": base64.b64encode(csv_data.encode("utf-8")),
            "file_name": "test_holidays.csv",
            "duplicate_policy": "skip",
        })

        wizard.action_parse_and_preview()
        self.assertEqual(wizard.state, "preview")
        self.assertEqual(len(wizard.preview_line_ids), 2)

        wizard.action_confirm_import()
        self.assertEqual(wizard.state, "done")
        self.assertTrue(wizard.import_log_id)
        self.assertEqual(wizard.import_log_id.records_created, 2)

        csv_update_data = (
            "Name,Date From,Date To,Holiday Type,Work Pay Multiplier,Note\n"
            "Midyear Festival,2026-06-10,2026-06-13,public,2.5,Updated 4 days\n"
        )
        wizard2 = self.env["wizard.import.public.holiday"].create({
            "file_data": base64.b64encode(csv_update_data.encode("utf-8")),
            "file_name": "test_update.csv",
            "duplicate_policy": "update",
        })
        wizard2.action_parse_and_preview()
        self.assertEqual(wizard2.preview_line_ids[0].status, "duplicate")
        wizard2.action_confirm_import()
        self.assertEqual(wizard2.import_log_id.records_updated, 1)

        updated_h = self.Holiday.search([("name", "=", "Midyear Festival")], limit=1)
        self.assertEqual(str(updated_h.date_to), "2026-06-13")
        self.assertEqual(updated_h.work_pay_multiplier, 2.5)

    def test_04_import_atomic_failure_on_invalid_data(self):
        """Test import stops on invalid data and rollback ensures nothing is created."""
        csv_bad_data = (
            "Name,Date From,Date To,Holiday Type,Work Pay Multiplier,Note\n"
            ",2026-02-01,2026-02-01,public,2.0,Missing name\n"
            "Invalid Date Holiday,NOT_A_DATE,2026-02-05,public,2.0,Invalid date\n"
        )
        wizard = self.env["wizard.import.public.holiday"].create({
            "file_data": base64.b64encode(csv_bad_data.encode("utf-8")),
            "file_name": "bad.csv",
        })
        wizard.action_parse_and_preview()
        self.assertGreater(wizard.error_rows, 0)
        with self.assertRaises(ValidationError):
            wizard.action_confirm_import()

    def test_05_template_download(self):
        """Test Download Template action returns downloadable attachment."""
        wizard = self.env["wizard.import.public.holiday"].create({
            "file_data": base64.b64encode(b"placeholder"),
            "file_name": "template.csv",
        })
        res = wizard.action_download_template()
        self.assertEqual(res.get("type"), "ir.actions.act_url")
        self.assertIn("/web/content/", res.get("url"))

    def test_06_session_scheduling_on_holiday_validation(self):
        """Test scheduling on holiday is blocked by default and allowed only for admin with reason."""
        h = self.Holiday.create({
            "name": "King Sihamoni Day Test",
            "date_from": "2026-05-14",
            "date_to": "2026-05-14",
            "applies_to": "all",
            "academic_year_id": self.ay.id,
        })

        dt_start = datetime(2026, 5, 14, 9, 0)
        dt_end = datetime(2026, 5, 14, 11, 0)

        with self.assertRaises(ValidationError):
            self.Slot.with_user(self.admin_user).create({
                "name": "Lecture on Holiday",
                "teacher_id": self.teacher.id,
                "section_id": self.section_a.id,
                "subject_id": self.subject.id,
                "start_time": dt_start,
                "end_time": dt_end,
                "allow_on_holiday": False,
            })

        with self.assertRaises(ValidationError):
            self.Slot.with_user(self.admin_user).create({
                "name": "Lecture on Holiday",
                "teacher_id": self.teacher.id,
                "section_id": self.section_a.id,
                "subject_id": self.subject.id,
                "start_time": dt_start,
                "end_time": dt_end,
                "allow_on_holiday": True,
                "holiday_override_reason": "",
            })

        slot = self.Slot.with_user(self.admin_user).create({
            "name": "Lecture on Holiday Allowed",
            "teacher_id": self.teacher.id,
            "section_id": self.section_a.id,
            "subject_id": self.subject.id,
            "start_time": dt_start,
            "end_time": dt_end,
            "allow_on_holiday": True,
            "holiday_override_reason": "Special Intensive Workshop approved by Dean",
        })
        self.assertTrue(slot.id)
        self.assertTrue(slot.on_holiday)
        self.assertEqual(slot.holiday_name, "King Sihamoni Day Test")

    def test_07_cancel_and_reschedule_conflict(self):
        """Test cancel_for_holiday and reschedule wizard."""
        h = self.Holiday.create({
            "name": "Phchum Ben Test Day",
            "date_from": "2026-10-10",
            "date_to": "2026-10-10",
            "applies_to": "all",
            "academic_year_id": self.ay.id,
        })
        slot = self.Slot.with_context(skip_holiday_check=True).create({
            "name": "Conflict Session",
            "teacher_id": self.teacher.id,
            "section_id": self.section_a.id,
            "subject_id": self.subject.id,
            "start_time": datetime(2026, 10, 10, 8, 0),
            "end_time": datetime(2026, 10, 10, 10, 0),
        })

        slot.action_cancel_for_holiday("Phchum Ben Test Day")
        self.assertEqual(slot.state, "cancelled")
        self.assertEqual(slot.cancel_reason, "Phchum Ben Test Day")

        slot2 = self.Slot.with_context(skip_holiday_check=True).create({
            "name": "Session to Reschedule",
            "teacher_id": self.teacher.id,
            "section_id": self.section_a.id,
            "subject_id": self.subject.id,
            "start_time": datetime(2026, 10, 10, 13, 0),
            "end_time": datetime(2026, 10, 10, 15, 0),
        })
        wizard = self.env["wizard.reschedule.session"].create({
            "slot_id": slot2.id,
            "new_start_time": datetime(2026, 10, 14, 13, 0),
            "new_end_time": datetime(2026, 10, 14, 15, 0),
            "reschedule_reason": "Shifted after holiday",
        })
        wizard.action_reschedule()
        self.assertEqual(slot2.start_time, datetime(2026, 10, 14, 13, 0))

    def test_08_class_section_holiday_conflict_count(self):
        """Test class section computes conflict count and flags red banner."""
        h = self.Holiday.create({
            "name": "Water Festival Test",
            "date_from": "2026-11-20",
            "date_to": "2026-11-22",
            "applies_to": "all",
            "academic_year_id": self.ay.id,
        })
        slot = self.Slot.with_context(skip_holiday_check=True).create({
            "name": "Conflicting Slot in Sec A",
            "teacher_id": self.teacher.id,
            "section_id": self.section_a.id,
            "subject_id": self.subject.id,
            "start_time": datetime(2026, 11, 20, 9, 0),
            "end_time": datetime(2026, 11, 20, 11, 0),
        })

        self.section_a._compute_holiday_conflicts()
        self.assertGreaterEqual(self.section_a.holiday_conflict_count, 1)
        self.assertTrue(self.section_a.has_holiday_conflicts)

    def test_09_staff_attendance_holiday_work_multiplier(self):
        """Test staff attendance on holiday pre-marks holiday and multiplies worked hours."""
        h = self.Holiday.search([("name", "=", "Constitutional Day")], limit=1)
        if not h:
            h = self.Holiday.create({
                "name": "Constitutional Day",
                "date_from": "2026-09-24",
                "date_to": "2026-09-24",
                "applies_to": "all",
                "work_pay_multiplier": 2.0,
                "academic_year_id": self.ay.id,
            })
        else:
            h.write({"work_pay_multiplier": 2.0})

        teacher = self.env["university.teacher"].search([], limit=1)
        if not teacher:
            teacher = self.env["university.teacher"].create({"name": "Test Instructor"})

        att = self.env["university.staff.attendance"].create({
            "staff_id": teacher.id,
            "date": "2026-09-24",
            "status": "absent",
            "worked_hours": 0.0,
        })
        self.assertTrue(att.is_holiday)
        self.assertEqual(att.status, "holiday")

        att.write({
            "status": "present",
            "check_in": "2026-09-24 08:00:00",
            "check_out": "2026-09-24 12:00:00",
            "worked_hours": 4.0,
        })
        self.assertTrue(att.is_holiday_work)
        self.assertEqual(att.holiday_work_pay_multiplier, 2.0)
        self.assertEqual(att.payable_hours, 8.0)

    def test_10_xlsx_import_with_various_rows(self):
        """Test XLSX import with good, duplicate, invalid, overlapping rows and atomic per-row failure."""
        if not openpyxl:
            return

        self.Holiday.create({
            "name": "Base Overlap Holiday",
            "date_from": "2026-03-10",
            "date_to": "2026-03-12",
            "applies_to": "all",
            "academic_year_id": self.ay.id,
        })

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Name", "Date From", "Date To", "Holiday Type", "Work Pay Multiplier", "Note"])
        ws.append(["Excel Good Holiday", "2026-03-20", "2026-03-21", "public", 2.0, "Good row"])
        ws.append(["Excel Good Holiday", "2026-03-20", "2026-03-21", "public", 2.0, "Duplicate in file"])
        ws.append(["Excel Bad Date", "NOT_A_DATE", "2026-03-25", "public", 2.0, "Invalid date"])
        ws.append(["Excel Clash Holiday", "2026-03-11", "2026-03-13", "public", 2.0, "Clash row"])

        buf = io.BytesIO()
        wb.save(buf)
        file_bytes = buf.getvalue()

        wizard = self.env["wizard.import.public.holiday"].create({
            "file_data": base64.b64encode(file_bytes),
            "file_name": "holidays_test.xlsx",
            "duplicate_policy": "skip",
        })

        wizard.action_parse_and_preview()
        self.assertEqual(wizard.state, "preview")
        self.assertEqual(wizard.total_rows, 4)
        self.assertGreaterEqual(wizard.error_rows, 1)
        self.assertGreaterEqual(wizard.duplicate_rows, 1)

        wizard.action_confirm_import()
        self.assertEqual(wizard.state, "done")
        self.assertTrue(wizard.import_log_id)
        created_h = self.Holiday.search([("name", "=", "Excel Good Holiday")], limit=1)
        self.assertTrue(created_h)
        self.assertGreaterEqual(wizard.import_log_id.records_failed, 1)

    def test_11_timetable_generation_skips_holidays_and_respects_checkbox(self):
        """Test timetable generation wizard skips holidays when skip_public_holidays=True and respects toggle."""
        h = self.Holiday.create({
            "name": "Mid-May Holiday",
            "date_from": "2026-05-20",
            "date_to": "2026-05-20",
            "applies_to": "all",
            "academic_year_id": self.ay.id,
        })
        wizard = self.env["university.timetable.generation.wizard"].new({
            "academic_year_id": self.ay.id,
            "semester_id": self.semester.id,
            "start_date": "2026-05-18",
            "week_count": 1,
            "skip_public_holidays": True,
        })
        excluded = wizard._get_excluded_dates(date(2026, 5, 18), date(2026, 5, 24))
        self.assertIn(date(2026, 5, 20), excluded)

        wizard.skip_public_holidays = False
        excluded_uncheck = wizard._get_excluded_dates(date(2026, 5, 18), date(2026, 5, 24))
        self.assertEqual(excluded_uncheck, set())

    def test_12_non_admin_cannot_override_holiday(self):
        """Test non-admin (e.g. teacher) cannot bypass holiday restriction even if allow_on_holiday is set."""
        h = self.Holiday.create({
            "name": "Mid-November Special Test Day",
            "date_from": "2026-11-15",
            "date_to": "2026-11-15",
            "applies_to": "all",
            "academic_year_id": self.ay.id,
        })
        dt_start = datetime(2026, 11, 15, 8, 0)
        dt_end = datetime(2026, 11, 15, 10, 0)

        slot_candidate = self.Slot.new({
            "name": "Teacher Session on Holiday",
            "teacher_id": self.teacher.id,
            "section_id": self.section_a.id,
            "subject_id": self.subject.id,
            "start_time": dt_start,
            "end_time": dt_end,
            "allow_on_holiday": True,
            "holiday_override_reason": "Teacher attempt",
        })
        with self.assertRaises(ValidationError) as cm:
            slot_candidate.with_user(self.teacher_user)._check_holiday_conflict()
        self.assertIn("Only School Administrators", str(cm.exception))

        with self.assertRaises(ValidationError) as cm2:
            self.Slot.create({
                "name": "Direct Session on Holiday",
                "teacher_id": self.teacher.id,
                "section_id": self.section_a.id,
                "subject_id": self.subject.id,
                "start_time": dt_start,
                "end_time": dt_end,
                "allow_on_holiday": False,
            })
        self.assertIn("Cannot schedule session", str(cm2.exception))

    def test_13_school_management_hook_defaults(self):
        """Test that default hooks in school_management return safe defaults without holiday data."""
        wizard = self.env["university.timetable.generation.wizard"].new()
        excluded = wizard._get_excluded_dates("2026-01-01", "2026-01-10")
        self.assertIsInstance(excluded, set)

        att = self.env["university.staff.attendance"].new()
        self.assertFalse(att._is_non_working_day(date(2026, 1, 15)))
        self.assertFalse(att._get_day_label(date(2026, 1, 15)))

        slot = self.env["university.timetable.slot"].new()
        self.assertFalse(slot._get_holiday_conflict())

    def test_14_onchange_start_time_holiday_warning(self):
        """Test onchange warning when selecting a public holiday date."""
        h = self.Holiday.create({
            "name": "Queen Mother Birthday Test",
            "date_from": "2026-06-18",
            "date_to": "2026-06-18",
            "applies_to": "all",
            "academic_year_id": self.ay.id,
        })
        slot = self.Slot.new({
            "section_id": self.section_a.id,
            "start_time": datetime(2026, 6, 18, 9, 0),
        })
        res = slot._onchange_start_time_holiday_warning()
        self.assertIsNotNone(res)
        self.assertIn("warning", res)
        self.assertIn("Queen Mother Birthday Test", res["warning"]["message"])

    def test_15_get_holiday_schedule_indicators_date_values(self):
        """Test retrieving holiday indicators compares and indexes by exact date values."""
        h = self.Holiday.create({
            "name": "Constitution Day Test",
            "date_from": "2026-09-24",
            "date_to": "2026-09-24",
            "applies_to": "all",
            "academic_year_id": self.ay.id,
        })
        indicators = self.Slot.get_holiday_schedule_indicators("2026-09-20", "2026-09-26")
        self.assertIn("2026-09-24", indicators["holiday_days"])
        self.assertEqual(indicators["holiday_days"]["2026-09-24"]["name"], "Constitution Day Test")
        self.assertEqual(indicators["holiday_days"]["2026-09-24"]["date_start"], "2026-09-24")

    def test_16_public_holiday_model_crud_and_validation(self):
        """Test public.holiday model fields, constraints, session_count and cancel actions."""
        # 1. Create valid public holiday
        ph = self.PublicHoliday.create({
            "name": "Test Meak Bochea",
            "name_km": "មាឃបូជា",
            "date_from": "2026-02-12",
            "date_to": "2026-02-12",
        })
        self.assertTrue(ph.id)
        self.assertEqual(ph.session_count, 0)

        # 2. Date order constraint
        with self.assertRaises(ValidationError):
            self.PublicHoliday.create({
                "name": "Invalid Date Holiday",
                "date_from": "2026-02-20",
                "date_to": "2026-02-15",
            })

        # 3. Duplicate name and date overlap constraint
        with self.assertRaises(ValidationError):
            self.PublicHoliday.create({
                "name": "Test Meak Bochea",
                "date_from": "2026-02-12",
                "date_to": "2026-02-13",
            })

        # 4. Schedule a slot using skip_holiday_check, confirm session_count computes it
        slot = self.Slot.with_context(skip_holiday_check=True).create({
            "name": "Conflict Meak Bochea Session",
            "teacher_id": self.teacher.id,
            "section_id": self.section_a.id,
            "subject_id": self.subject.id,
            "start_time": datetime(2026, 2, 12, 8, 0),
            "end_time": datetime(2026, 2, 12, 10, 0),
        })
        ph._compute_session_count()
        self.assertEqual(ph.session_count, 1)

        # 5. Cancel affected sessions button
        ph.action_cancel_affected_sessions()
        self.assertEqual(slot.state, "cancelled")
        ph._compute_session_count()
        self.assertEqual(ph.session_count, 0)

        # 6. Attempting to schedule a NEW session without bypass raises ValidationError
        with self.assertRaises(ValidationError):
            self.Slot.create({
                "name": "Blocked Holiday Class",
                "teacher_id": self.teacher.id,
                "section_id": self.section_a.id,
                "subject_id": self.subject.id,
                "start_time": datetime(2026, 2, 12, 14, 0),
                "end_time": datetime(2026, 2, 12, 16, 0),
            })

    def test_17_public_holiday_import_wizard(self):
        """Test wizard.import.public.holiday CSV parsing, duplicate policy, fixed generation and template download."""
        wizard = self.env["wizard.import.public.holiday"].create({
            "target_year": 2026,
        })
        dl = wizard.action_download_template()
        self.assertEqual(dl.get("type"), "ir.actions.act_url")

        gen_res = wizard.action_generate_fixed_holidays()
        self.assertEqual(gen_res.get("type"), "ir.actions.client")
        new_year = self.PublicHoliday.search([("name", "=", "International New Year"), ("date_from", "=", "2026-01-01")])
        self.assertTrue(new_year)

        csv_data = (
            "Name,Name KM,Date From,Date To,Holiday Type,Work Pay Multiplier,Note\n"
            "Preah Vihear Temple Day,ទិវាប្រាសាទព្រះវិហារ,2026-07-07,2026-07-07,special,2.0,Temple Anniversary\n"
            "National Reading Day,ទិវាជាតិអំណាន,2026-03-11,2026-03-11,special,2.0,Reading Day\n"
            "Preah Vihear Temple Day,ទិវាប្រាសាទព្រះវិហារ,2026-07-07,2026-07-07,special,2.0,Duplicate Row\n"
        )
        wizard_csv = self.env["wizard.import.public.holiday"].create({
            "file_data": base64.b64encode(csv_data.encode("utf-8")),
            "file_name": "cambodia_extra.csv",
            "duplicate_policy": "skip",
        })
        wizard_csv.action_parse_and_preview()
        self.assertEqual(wizard_csv.state, "preview")
        self.assertEqual(wizard_csv.total_rows, 3)
        self.assertEqual(wizard_csv.valid_rows, 2)
        self.assertEqual(wizard_csv.duplicate_rows, 1)

        wizard_csv.action_confirm_import()
        self.assertEqual(wizard_csv.state, "done")
        created_ph = self.PublicHoliday.search([("name", "=", "Preah Vihear Temple Day")])
        self.assertEqual(len(created_ph), 1)

    def test_19_holiday_canonical_hooks(self):
        """Test public.holiday canonical lookup methods and admin check."""
        h = self.PublicHoliday.create({
            "name": "Hook Holiday Test",
            "date_from": "2026-08-15",
            "date_to": "2026-08-15",
            "active": True,
        })
        found = self.PublicHoliday.get_holiday_on("2026-08-15")
        self.assertEqual(found.id, h.id)
        self.assertTrue(self.PublicHoliday.is_holiday("2026-08-15"))
        self.assertFalse(self.PublicHoliday.is_holiday("2026-08-17"))

        self.assertTrue(self.PublicHoliday.with_user(self.admin_user)._is_holiday_admin())
        self.assertFalse(self.PublicHoliday.with_user(self.teacher_user)._is_holiday_admin())

    def test_18_public_holiday_security(self):
        """Test access rights on public.holiday model."""
        holidays_read = self.PublicHoliday.with_user(self.teacher_user).search([])
        self.assertGreaterEqual(len(holidays_read), 0)

        with self.assertRaises(AccessError):
            self.PublicHoliday.with_user(self.teacher_user).create({
                "name": "Unauthorized Holiday",
                "date_from": "2026-12-25",
                "date_to": "2026-12-25",
            })
