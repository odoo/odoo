import secrets
from datetime import timedelta

from odoo import Command, fields
from odoo.tests.common import TransactionCase


class StudyPlanCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set user timezone to Asia/Phnom_Penh so timezone logic is exercised
        cls.env.user.tz = "Asia/Phnom_Penh"

        today = fields.Date.today()
        # Find next Monday (relative to today, skipping any holiday period)
        cur = today + timedelta(days=((0 - today.weekday()) % 7 or 7))
        PublicHoliday = cls.env["public.holiday"] if "public.holiday" in cls.env else None
        while True:
            if PublicHoliday is not None:
                hols = PublicHoliday.search_count([
                    ("date_from", "<=", cur + timedelta(days=28)),
                    ("date_to", ">=", cur),
                    ("active", "=", True),
                ])
                if hols:
                    cur += timedelta(days=7)
                    continue
            break
        cls.next_monday = cur

        # 1. Academic Year & Semester (covering next ~8-10 weeks)
        ay_domain = [
            ("date_start", "<=", cls.next_monday),
            ("date_end", ">=", cls.next_monday),
        ]
        existing_ay = cls.env["university.academic.year"].search(ay_domain, limit=1)
        if existing_ay:
            cls.academic_year = existing_ay
        else:
            cls.academic_year = cls.env["university.academic.year"].create({
                "name": f"Test AY {today.year}_{secrets.token_hex(4)}",
                "date_start": cls.next_monday - timedelta(days=30),
                "date_end": cls.next_monday + timedelta(days=300),
                "state": "running",
            })

        sem_domain = [
            ("academic_year_id", "=", cls.academic_year.id),
            ("date_start", "<=", cls.next_monday),
            ("date_end", ">=", cls.next_monday),
        ]
        existing_sem = cls.env["university.semester"].search(sem_domain, limit=1)
        if existing_sem:
            cls.semester = existing_sem
        else:
            cls.semester = cls.env["university.semester"].create({
                "name": f"Test Sem {today.year}_{secrets.token_hex(4)}",
                "academic_year_id": cls.academic_year.id,
                "semester_type": "semester_1",
                "date_start": cls.next_monday - timedelta(days=7),
                "date_end": cls.next_monday + timedelta(days=70),
            })

        # Academic infrastructure
        cls.faculty = cls.env["university.faculty"].create({
            "name": f"Faculty of Science {secrets.token_hex(3)}",
            "code": f"FSC_{secrets.token_hex(3).upper()}",
        })
        cls.department = cls.env["university.department"].create({
            "name": f"Computer Science {secrets.token_hex(3)}",
            "code": f"CS_{secrets.token_hex(3).upper()}",
            "faculty_id": cls.faculty.id,
        })
        cls.program = cls.env["university.program"].create({
            "name": f"B.S. Software Engineering {secrets.token_hex(3)}",
            "code": f"SE_{secrets.token_hex(3).upper()}",
            "faculty_id": cls.faculty.id,
            "department_id": cls.department.id,
            "degree_type": "bachelor",
        })

        # 2. Teacher & User
        cls.group_teacher = cls.env.ref("school_management.group_school_teacher")
        cls.teacher_user = cls.env["res.users"].create({
            "name": "Teacher Alice",
            "login": f"teacher_alice_{secrets.token_hex(4)}@test.com",
            "email": "teacher_alice@test.com",
            "group_ids": [Command.set([cls.group_teacher.id])],
            "tz": "Asia/Phnom_Penh",
        })
        cls.teacher = cls.env["university.teacher"].create({
            "name": "Prof. Alice",
            "user_id": cls.teacher_user.id,
            "faculty_id": cls.faculty.id,
            "department_id": cls.department.id,
        })

        # 3. 3 Subjects
        cls.subject_1 = cls.env["university.subject"].create({
            "name": f"Algorithms {secrets.token_hex(2)}",
            "code": f"CS1_{secrets.token_hex(2).upper()}",
            "department_id": cls.department.id,
            "program_ids": [Command.set([cls.program.id])],
            "teacher_ids": [Command.set([cls.teacher.id])],
        })
        cls.subject_2 = cls.env["university.subject"].create({
            "name": f"Databases {secrets.token_hex(2)}",
            "code": f"CS2_{secrets.token_hex(2).upper()}",
            "department_id": cls.department.id,
            "program_ids": [Command.set([cls.program.id])],
            "teacher_ids": [Command.set([cls.teacher.id])],
        })
        cls.subject_3 = cls.env["university.subject"].create({
            "name": f"Networks {secrets.token_hex(2)}",
            "code": f"CS3_{secrets.token_hex(2).upper()}",
            "department_id": cls.department.id,
            "program_ids": [Command.set([cls.program.id])],
            "teacher_ids": [Command.set([cls.teacher.id])],
        })
        cls.subjects = cls.subject_1 | cls.subject_2 | cls.subject_3

        # 4. Class Section & Classroom
        cls.classroom = cls.env["university.classroom"].create({
            "name": f"Room {secrets.token_hex(2).upper()}",
            "capacity": 50,
        })
        cls.class_section = cls.env["university.class.section"].create({
            "name": f"SEC_{secrets.token_hex(3).upper()}",
            "program_id": cls.program.id,
            "semester_id": cls.semester.id,
            "teacher_id": cls.teacher.id,
            "classroom_id": cls.classroom.id,
            "capacity": 40,
        })

        # 5. Student & User with active enrollment in that section
        cls.group_student = cls.env.ref("school_management.group_school_student")
        cls.student_user = cls.env["res.users"].create({
            "name": "Student Bob",
            "login": f"student_bob_{secrets.token_hex(4)}@test.com",
            "email": "student_bob@test.com",
            "group_ids": [Command.set([cls.group_student.id])],
            "tz": "Asia/Phnom_Penh",
        })
        cls.student = cls.env["university.student"].create({
            "name": "Student Bob",
            "student_id": f"STD_{secrets.token_hex(3).upper()}",
            "user_id": cls.student_user.id,
            "program_id": cls.program.id,
            "faculty_id": cls.faculty.id,
            "department_id": cls.department.id,
            "academic_year_id": cls.academic_year.id,
            "current_semester_id": cls.semester.id,
            "status": "active",
        })
        cls.enrollment = cls.env["university.enrollment"].with_context(bypass_registration_window=True).create({
            "student_id": cls.student.id,
            "class_section_id": cls.class_section.id,
            "status": "enrolled",
        })

        # 6. 5 Timeslots:
        # Mon 08:00-09:30, Mon 10:00-11:30, Wed 08:00-09:30, Wed 10:00-11:30, Sat 08:00-09:00
        Timeslot = cls.env["university.timeslot"]

        def _get_or_create_slot(day, s_h, e_h):
            slot = Timeslot.search([
                ("day_of_week", "=", day),
                ("start_hour", "=", s_h),
                ("end_hour", "=", e_h),
            ], limit=1)
            if not slot:
                slot = Timeslot.create({
                    "day_of_week": day,
                    "start_hour": s_h,
                    "end_hour": e_h,
                })
            return slot

        cls.slot_mon_1 = _get_or_create_slot("0", 8.0, 9.5)
        cls.slot_mon_2 = _get_or_create_slot("0", 10.0, 11.5)
        cls.slot_wed_1 = _get_or_create_slot("2", 8.0, 9.5)
        cls.slot_wed_2 = _get_or_create_slot("2", 10.0, 11.5)
        cls.slot_sat_1 = _get_or_create_slot("5", 8.0, 9.0)
        cls.timeslots = cls.slot_mon_1 | cls.slot_mon_2 | cls.slot_wed_1 | cls.slot_wed_2 | cls.slot_sat_1

        # 7. Published timetable sessions for 4 weeks (generation_state = "published")
        wizard = cls.env["university.timetable.generation.wizard"].create({
            "academic_year_id": cls.academic_year.id,
            "semester_id": cls.semester.id,
            "section_ids": [Command.set([cls.class_section.id])],
            "timeslot_ids": [Command.set(cls.timeslots.ids)],
            "start_date": cls.next_monday,
            "week_count": 4,
            "sessions_per_week": 1,
        })
        wizard.action_generate_timetable()
        cls.published_slots = cls.env["university.timetable.slot"].search([
            ("section_id", "=", cls.class_section.id),
            ("start_time", ">=", cls.next_monday),
        ])
        cls.published_slots.write({"generation_state": "published"})
