import secrets
from datetime import datetime, time, timedelta
import pytz

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from ..common import StudyPlanCommon


@tagged("post_install", "-at_install", "school_management")
class TestWeeklyScheduleTimetable(StudyPlanCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.timeslot_mon = cls.slot_mon_1
        cls.timeslot_wed = cls.slot_wed_1

    def test_01_weekly_lines_and_summary_computation(self):
        """Weekly schedule lines compute day and time summary on class section."""
        section = self.env["university.class.section"].create({
            "name": f"Data Structures - Sec {secrets.token_hex(2).upper()}",
            "program_id": self.program.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "semester_id": self.semester.id,
            "capacity": 30,
        })
        # Create weekly lines for Monday and Wednesday
        self.env["university.class.schedule.line"].create([
            {
                "class_id": section.id,
                "weekday": "0",
                "timeslot_id": self.timeslot_mon.id,
                "room_id": self.classroom.id,
                "teacher_id": self.teacher.id,
            },
            {
                "class_id": section.id,
                "weekday": "2",
                "timeslot_id": self.timeslot_wed.id,
                "room_id": self.classroom.id,
                "teacher_id": self.teacher.id,
            },
        ])
        section._compute_schedule_summary()
        self.assertIn("Mon", section.day_summary)
        self.assertIn("Wed", section.day_summary)
        self.assertIn("08:00", section.time_summary)

    def test_02_generate_timetable_and_skip_public_holidays(self):
        """Wizard generates dated sessions across term dates and skips public holidays."""
        section = self.env["university.class.section"].create({
            "name": f"Data Structures - B {secrets.token_hex(2).upper()}",
            "program_id": self.program.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "semester_id": self.semester.id,
            "capacity": 30,
        })
        self.env["university.class.schedule.line"].create([
            {
                "class_id": section.id,
                "weekday": "0",
                "timeslot_id": self.timeslot_mon.id,
                "room_id": self.classroom.id,
                "teacher_id": self.teacher.id,
            },
            {
                "class_id": section.id,
                "weekday": "2",
                "timeslot_id": self.timeslot_wed.id,
                "room_id": self.classroom.id,
                "teacher_id": self.teacher.id,
            },
        ])

        # Pick a Monday within the semester date range to set as a public holiday
        term_start = self.semester.date_start
        term_end = self.semester.date_end
        holiday_date = None
        cur = term_start
        while cur <= term_end:
            if cur.weekday() == 0:  # Monday
                holiday_date = cur
                break
            cur += timedelta(days=1)
        self.assertTrue(holiday_date, "A Monday should exist in the term.")

        if "public.holiday" in self.env:
            holiday = self.env["public.holiday"].create({
                "name": f"Test Holiday {secrets.token_hex(2)}",
                "date_from": holiday_date,
                "date_to": holiday_date,
                "active": True,
            })
        else:
            holiday = self.env["university.holiday"].create({
                "name": f"Test Holiday {secrets.token_hex(2)}",
                "academic_year_id": self.academic_year.id,
                "date_start": holiday_date,
                "date_end": holiday_date,
            })

        wizard = self.env["university.timetable.generation.wizard"].create({
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "section_ids": [Command.set([section.id])],
        })
        res = wizard.action_generate_timetable()
        self.assertTrue(res)

        slots = self.env["university.timetable.slot"].search([("section_id", "=", section.id)])
        self.assertTrue(slots, "Sessions should have been generated.")

        # Ensure no session was created on the holiday date
        tz = pytz.timezone(self.env.user.tz or "UTC")
        slot_dates = [
            pytz.utc.localize(s.start_time).astimezone(tz).date()
            for s in slots
        ]
        self.assertNotIn(holiday_date, slot_dates, "Sessions must not be scheduled on public holiday.")

        # Idempotency check: Running wizard again must not duplicate sessions
        count_before = len(slots)
        wizard.action_generate_timetable()
        slots_after = self.env["university.timetable.slot"].search([("section_id", "=", section.id)])
        self.assertEqual(len(slots_after), count_before, "Running wizard twice must be idempotent.")

    def test_03_teacher_conflict_prevention(self):
        """Prevent scheduling the same teacher in two overlapping sessions."""
        Slot = self.env["university.timetable.slot"]
        dt_start = datetime.combine(self.next_monday, time(8, 0))
        dt_end = datetime.combine(self.next_monday, time(10, 0))

        sec1 = self.env["university.class.section"].create({
            "name": "Sec Teacher Conf 1",
            "program_id": self.program.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "semester_id": self.semester.id,
            "capacity": 30,
        })
        sec2 = self.env["university.class.section"].create({
            "name": "Sec Teacher Conf 2",
            "program_id": self.program.id,
            "subject_id": self.subject_2.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "semester_id": self.semester.id,
            "capacity": 30,
        })

        Slot.create({
            "section_id": sec1.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "start_time": dt_start,
            "end_time": dt_end,
            "state": "scheduled",
        })

        with self.assertRaises(ValidationError):
            Slot.create({
                "section_id": sec2.id,
                "subject_id": self.subject_2.id,
                "teacher_id": self.teacher.id,
                "classroom_id": self.classroom.id,
                "start_time": dt_start,
                "end_time": dt_end,
                "state": "scheduled",
            })

    def test_04_room_conflict_prevention(self):
        """Prevent scheduling the same classroom in two overlapping sessions."""
        Slot = self.env["university.timetable.slot"]
        dt_start = datetime.combine(self.next_monday + timedelta(days=1), time(8, 0))
        dt_end = datetime.combine(self.next_monday + timedelta(days=1), time(10, 0))

        other_teacher = self.env["university.teacher"].create({
            "name": "Prof. Bob",
            "faculty_id": self.faculty.id,
            "department_id": self.department.id,
            "subject_ids": [Command.link(self.subject_2.id)],
        })
        sec1 = self.env["university.class.section"].create({
            "name": "Sec Room Conf 1",
            "program_id": self.program.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "semester_id": self.semester.id,
            "capacity": 30,
        })
        sec2 = self.env["university.class.section"].create({
            "name": "Sec Room Conf 2",
            "program_id": self.program.id,
            "subject_id": self.subject_2.id,
            "teacher_id": other_teacher.id,
            "classroom_id": self.classroom.id,
            "semester_id": self.semester.id,
            "capacity": 30,
        })

        Slot.create({
            "section_id": sec1.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "start_time": dt_start,
            "end_time": dt_end,
            "state": "scheduled",
        })

        with self.assertRaises(ValidationError):
            Slot.create({
                "section_id": sec2.id,
                "subject_id": self.subject_2.id,
                "teacher_id": other_teacher.id,
                "classroom_id": self.classroom.id,
                "start_time": dt_start,
                "end_time": dt_end,
                "state": "scheduled",
            })

    def test_05_student_schedule_overlap_warning(self):
        """Onchange warns when student is enrolled in overlapping class section."""
        sec_overlap_1 = self.env["university.class.section"].create({
            "name": "Overlap Sec 1",
            "program_id": self.program.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "semester_id": self.semester.id,
            "capacity": 30,
        })
        sec_overlap_2 = self.env["university.class.section"].create({
            "name": "Overlap Sec 2",
            "program_id": self.program.id,
            "subject_id": self.subject_2.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "semester_id": self.semester.id,
            "capacity": 30,
        })
        self.env["university.class.schedule.line"].create([
            {
                "class_id": sec_overlap_1.id,
                "weekday": "0",
                "timeslot_id": self.timeslot_mon.id,
            },
            {
                "class_id": sec_overlap_2.id,
                "weekday": "0",
                "timeslot_id": self.timeslot_mon.id,
            },
        ])

        # Student enrolled in sec_overlap_1
        self.env["university.enrollment"].with_context(bypass_registration_window=True).create({
            "student_id": self.student.id,
            "class_section_id": sec_overlap_1.id,
            "status": "enrolled",
        })

        # Check onchange warning when selecting sec_overlap_2
        new_enrollment = self.env["university.enrollment"].new({
            "student_id": self.student.id,
            "class_section_id": sec_overlap_2.id,
        })
        res = new_enrollment._onchange_class_section_or_student()
        self.assertTrue(res and "warning" in res, "Onchange should return a schedule overlap warning.")
        self.assertIn("Schedule Overlap Warning", res["warning"]["title"])

    def test_06_student_my_timetable_security(self):
        """Students only see published sessions of their own active enrollments."""
        Slot = self.env["university.timetable.slot"]
        dt_start = datetime.combine(self.next_monday + timedelta(days=2), time(8, 0))
        dt_end = datetime.combine(self.next_monday + timedelta(days=2), time(10, 0))

        draft_slot = Slot.create({
            "section_id": self.class_section.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "start_time": dt_start,
            "end_time": dt_end,
            "generation_state": "draft",
            "state": "scheduled",
        })
        pub_slot = Slot.create({
            "section_id": self.class_section.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "start_time": dt_start + timedelta(days=7),
            "end_time": dt_end + timedelta(days=7),
            "generation_state": "published",
            "state": "published",
        })

        # Guest instructor on the slot (differs from section.teacher_id)
        guest = self.env["university.teacher"].create({
            "name": "Prof. Guest Instructor",
            "faculty_id": self.faculty.id,
            "department_id": self.department.id,
        })
        guest_slot = Slot.create({
            "section_id": self.class_section.id,
            "subject_id": self.subject_1.id,
            "teacher_id": guest.id,
            "classroom_id": self.classroom.id,
            "start_time": dt_start + timedelta(days=14),
            "end_time": dt_end + timedelta(days=14),
            "generation_state": "published",
            "state": "published",
        })

        # Read as student user
        slots_as_student = Slot.with_user(self.student_user).search([
            ("id", "in", (draft_slot.id, pub_slot.id, guest_slot.id))
        ])
        self.assertIn(pub_slot, slots_as_student, "Published session must be visible to enrolled student.")
        self.assertIn(guest_slot, slots_as_student, "Published guest-instructor session must be visible.")
        self.assertNotIn(draft_slot, slots_as_student, "Draft session must not be visible to student.")

        # Calendar search_read must not AccessError on guest instructor / display_name
        rows = Slot.with_user(self.student_user).search_read(
            [("id", "=", guest_slot.id)],
            ["display_name", "teacher_id", "teacher_user_id"],
        )
        self.assertEqual(len(rows), 1)
        self.assertIn("Guest Instructor", rows[0]["display_name"])
        self.assertEqual(rows[0]["teacher_id"][0], guest.id)
        self.assertTrue(
            self.env["university.teacher"].with_user(self.student_user).browse(guest.id).exists(),
            "Student must be allowed to read the slot instructor.",
        )


    def test_07_comprehensive_role_based_access_control(self):
        """Comprehensive verification of timetable RBAC across Admin, Teacher, and Student roles."""
        Slot = self.env["university.timetable.slot"]
        admin_user = self.env.ref("base.user_admin")

        # 1. Setup Second Teacher and Second Section
        group_teacher = self.env.ref("school_management.group_school_teacher")
        charlie_user = self.env["res.users"].create({
            "name": "Teacher Charlie",
            "login": f"charlie_{secrets.token_hex(4)}@test.com",
            "email": "charlie@test.com",
            "group_ids": [Command.set([group_teacher.id])],
            "tz": "Asia/Phnom_Penh",
        })
        teacher_charlie = self.env["university.teacher"].create({
            "name": "Prof. Charlie",
            "user_id": charlie_user.id,
            "faculty_id": self.faculty.id,
            "department_id": self.department.id,
        })
        classroom_b = self.env["university.classroom"].create({
            "name": f"Room B {secrets.token_hex(2).upper()}",
            "capacity": 50,
        })
        sec_b = self.env["university.class.section"].create({
            "name": f"SEC_B_{secrets.token_hex(3).upper()}",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
            "teacher_id": teacher_charlie.id,
            "classroom_id": classroom_b.id,
            "capacity": 30,
        })

        # 2. Setup Student B (Eve) enrolled in sec_b
        group_student = self.env.ref("school_management.group_school_student")
        eve_user = self.env["res.users"].create({
            "name": "Student Eve",
            "login": f"eve_{secrets.token_hex(4)}@test.com",
            "email": "eve@test.com",
            "group_ids": [Command.set([group_student.id])],
            "tz": "Asia/Phnom_Penh",
        })
        student_eve = self.env["university.student"].create({
            "name": "Student Eve",
            "student_id": f"STD_EVE_{secrets.token_hex(3).upper()}",
            "user_id": eve_user.id,
            "program_id": self.program.id,
            "faculty_id": self.faculty.id,
            "department_id": self.department.id,
            "academic_year_id": self.academic_year.id,
            "current_semester_id": self.semester.id,
            "status": "active",
        })
        enrollment_eve = self.env["university.enrollment"].with_context(bypass_registration_window=True).create({
            "student_id": student_eve.id,
            "class_section_id": sec_b.id,
            "status": "enrolled",
        })

        # 3. Setup Student C (un-enrolled student)
        c_user = self.env["res.users"].create({
            "name": "Student Unenrolled",
            "login": f"unenrolled_{secrets.token_hex(4)}@test.com",
            "email": "unenrolled@test.com",
            "group_ids": [Command.set([group_student.id])],
            "tz": "Asia/Phnom_Penh",
        })
        student_c = self.env["university.student"].create({
            "name": "Student Unenrolled",
            "student_id": f"STD_NONE_{secrets.token_hex(3).upper()}",
            "user_id": c_user.id,
            "program_id": self.program.id,
            "faculty_id": self.faculty.id,
            "department_id": self.department.id,
            "academic_year_id": self.academic_year.id,
            "current_semester_id": self.semester.id,
            "status": "active",
        })

        # 4. Create Slots
        dt_start = datetime.combine(self.next_monday + timedelta(days=3), time(9, 0))
        dt_end = datetime.combine(self.next_monday + timedelta(days=3), time(11, 0))

        # Slot 1: Section A (Bob enrolled, Alice teaches, published)
        slot_a_pub = Slot.create({
            "section_id": self.class_section.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "start_time": dt_start,
            "end_time": dt_end,
            "generation_state": "published",
            "state": "published",
        })
        # Slot 2: Section B (Eve enrolled, Charlie teaches, published)
        slot_b_pub = Slot.create({
            "section_id": sec_b.id,
            "subject_id": self.subject_2.id,
            "teacher_id": teacher_charlie.id,
            "classroom_id": classroom_b.id,
            "start_time": dt_start,
            "end_time": dt_end,
            "generation_state": "published",
            "state": "published",
        })
        # Slot 3: Section A (Bob enrolled, Alice teaches, draft)
        slot_a_draft = Slot.create({
            "section_id": self.class_section.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "start_time": dt_start + timedelta(days=7),
            "end_time": dt_end + timedelta(days=7),
            "generation_state": "draft",
            "state": "draft",
        })

        all_test_slot_ids = [slot_a_pub.id, slot_b_pub.id, slot_a_draft.id]

        # -------------------------------------------------------------
        # Scenario A: Administrator
        # -------------------------------------------------------------
        admin_slots = Slot.with_user(admin_user).search([("id", "in", all_test_slot_ids)])
        self.assertEqual(len(admin_slots), 3, "Administrator must see all timetable slots.")
        # Admin can create slot
        admin_new_slot = Slot.with_user(admin_user).create({
            "section_id": self.class_section.id,
            "subject_id": self.subject_1.id,
            "teacher_id": self.teacher.id,
            "classroom_id": self.classroom.id,
            "start_time": dt_start + timedelta(days=14),
            "end_time": dt_end + timedelta(days=14),
            "generation_state": "published",
            "state": "published",
        })
        self.assertTrue(admin_new_slot.id, "Administrator can create timetable slots.")
        # Admin can edit slot
        admin_new_slot.with_user(admin_user).write({"notes": "Updated by Admin"})
        self.assertEqual(admin_new_slot.notes, "Updated by Admin")
        # Admin can access Gantt data
        date_str = dt_start.strftime("%Y-%m-%d")
        gantt_admin = Slot.with_user(admin_user).get_gantt_data(date_str, date_str)
        self.assertIn("resources", gantt_admin)
        self.assertTrue(len(gantt_admin["resources"]) >= 2, "Admin sees multiple teachers in Gantt resources.")

        # -------------------------------------------------------------
        # Scenario B: Teacher
        # -------------------------------------------------------------
        # Teacher Alice sees her own slots, not Charlie's
        alice_slots = Slot.with_user(self.teacher_user).search([("id", "in", all_test_slot_ids)])
        self.assertIn(slot_a_pub, alice_slots, "Teacher Alice sees her assigned slot.")
        self.assertIn(slot_a_draft, alice_slots, "Teacher Alice sees her assigned draft slot.")
        self.assertNotIn(slot_b_pub, alice_slots, "Teacher Alice cannot see Teacher Charlie's slot.")

        # Teacher Charlie sees only sec_b slot
        charlie_slots = Slot.with_user(charlie_user).search([("id", "in", all_test_slot_ids)])
        self.assertIn(slot_b_pub, charlie_slots, "Teacher Charlie sees his assigned slot.")
        self.assertNotIn(slot_a_pub, charlie_slots, "Teacher Charlie cannot see Teacher Alice's slot.")

        # Teacher Gantt view is scoped to own resource
        gantt_alice = Slot.with_user(self.teacher_user).get_gantt_data(date_str, date_str)
        alice_resource_ids = [r["name"] for r in gantt_alice["resources"]]
        self.assertIn(self.teacher.name, alice_resource_ids)
        self.assertNotIn(teacher_charlie.name, alice_resource_ids, "Teacher Alice must not see Charlie in Gantt resources.")

        # -------------------------------------------------------------
        # Scenario C: Student A (Bob)
        # -------------------------------------------------------------
        bob_slots = Slot.with_user(self.student_user).search([("id", "in", all_test_slot_ids)])
        self.assertIn(slot_a_pub, bob_slots, "Student Bob can see his enrolled section's published slot.")
        self.assertNotIn(slot_b_pub, bob_slots, "Student Bob cannot see un-enrolled section B slot.")
        self.assertNotIn(slot_a_draft, bob_slots, "Student Bob cannot see draft slots.")

        # Direct search of unrelated slot B must be empty due to record rules
        self.assertFalse(
            Slot.with_user(self.student_user).search([("id", "=", slot_b_pub.id)]),
            "Student Bob direct search of un-enrolled slot must return empty.",
        )
        # Direct read of unrelated slot B must raise AccessError
        with self.assertRaises(AccessError):
            Slot.with_user(self.student_user).browse(slot_b_pub.id).read(["name", "start_time"])

        # Student Bob cannot modify, create, or delete timetable records
        with self.assertRaises(AccessError):
            slot_a_pub.with_user(self.student_user).write({"notes": "Hacked by student"})
        with self.assertRaises(AccessError):
            Slot.with_user(self.student_user).create({
                "section_id": self.class_section.id,
                "subject_id": self.subject_1.id,
                "start_time": dt_start,
                "end_time": dt_end,
            })
        with self.assertRaises(AccessError):
            slot_a_pub.with_user(self.student_user).unlink()

        # Student Bob cannot read Student Eve's enrollment records
        self.assertFalse(
            self.env["university.enrollment"].with_user(self.student_user).search([("id", "=", enrollment_eve.id)]),
            "Student Bob search for Student Eve's enrollment record must return empty.",
        )
        with self.assertRaises(AccessError):
            self.env["university.enrollment"].with_user(self.student_user).browse(enrollment_eve.id).read(["student_id"])

        # Student Bob cannot access administrative Gantt resource scheduling
        with self.assertRaises(AccessError):
            Slot.with_user(self.student_user).get_gantt_data(date_str, date_str)

        # Student Bob cannot publish shifts
        with self.assertRaises(AccessError):
            Slot.with_user(self.student_user).action_publish_week_shifts(date_str, date_str)

        # -------------------------------------------------------------
        # Scenario D: Student B (Eve)
        # -------------------------------------------------------------
        eve_slots = Slot.with_user(eve_user).search([("id", "in", all_test_slot_ids)])
        self.assertIn(slot_b_pub, eve_slots, "Student Eve can see her enrolled section B slot.")
        self.assertNotIn(slot_a_pub, eve_slots, "Student Eve cannot see un-enrolled section A slot.")
        self.assertNotIn(slot_a_draft, eve_slots, "Student Eve cannot see section A draft slot.")

        # -------------------------------------------------------------
        # Scenario E: Student Without Enrollment
        # -------------------------------------------------------------
        c_slots = Slot.with_user(c_user).search([("id", "in", all_test_slot_ids)])
        self.assertFalse(c_slots, "Student without enrollments must see zero timetable slots.")

        # Unified schedule API returns empty for unenrolled student
        sched_res = Slot.with_user(c_user).get_schedule(date_str, date_str)
        self.assertEqual(sched_res.get("status"), "empty")
        self.assertEqual(sched_res.get("total_count"), 0)
        self.assertEqual(len(sched_res.get("sessions", [])), 0)

        # -------------------------------------------------------------
        # Scenario F: UI Action & View Security
        # -------------------------------------------------------------
        # Administrative action must not have Student in allowed groups
        admin_action = self.env.ref("school_management.action_university_timetable_slot")
        self.assertNotIn(
            group_student,
            admin_action.group_ids,
            "Administrative timetable action must not be accessible to student group.",
        )

        # Student action must not contain 'gantt' in view_mode
        student_action = self.env.ref("school_management.action_university_timetable_slot_student")
        self.assertNotIn("gantt", student_action.view_mode, "Student action view_mode must not contain gantt.")
        self.assertEqual(student_action.name, "My Study Schedule")
