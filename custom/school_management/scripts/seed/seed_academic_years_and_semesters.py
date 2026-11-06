import datetime
import random
from odoo.tools import config
config.parse_config(["-c", "odoo.conf", "-d", "odoo"])
from odoo.modules.registry import Registry
import odoo.api as api

reg = Registry("odoo")

with reg.cursor() as cr:
    env = api.Environment(cr, 1, {})
    
    print("=== 1. ACADEMIC YEAR 2024-2025 SETUP ===")
    y24 = env["university.academic.year"].search([("name", "ilike", "2024-2025")], limit=1)
    if not y24:
        y24 = env["university.academic.year"].create({
            "name": "2024-2025",
            "date_start": "2024-09-01",
            "date_end": "2025-06-30",
            "state": "running",
            "current": False,
        })
    else:
        y24.write({
            "state": "running",
            "date_start": "2024-09-01",
            "date_end": "2025-06-30",
        })
    print(f"Academic Year 2024-2025 (ID {y24.id}): State={y24.state}")

    # Semesters for 2024-2025
    s1_24 = env["university.semester"].search([("academic_year_id", "=", y24.id), ("semester_type", "=", "semester_1")], limit=1)
    if not s1_24:
        s1_24 = env["university.semester"].create({
            "academic_year_id": y24.id,
            "session_id": y24.id,
            "semester_type": "semester_1",
            "date_start": "2024-09-02",
            "date_end": "2025-01-17",
        })
    print(f"  Semester 1 2024-2025 (ID {s1_24.id})")

    s2_24 = env["university.semester"].search([("academic_year_id", "=", y24.id), ("semester_type", "=", "semester_2")], limit=1)
    if not s2_24:
        s2_24 = env["university.semester"].create({
            "academic_year_id": y24.id,
            "session_id": y24.id,
            "semester_type": "semester_2",
            "date_start": "2025-02-03",
            "date_end": "2025-06-20",
        })
    print(f"  Semester 2 2024-2025 (ID {s2_24.id})")

    # Get years 2025-2026 and 2026-2027
    y25 = env["university.academic.year"].search([("name", "ilike", "2025-2026")], limit=1)
    s1_25 = env["university.semester"].search([("academic_year_id", "=", y25.id), ("semester_type", "=", "semester_1")], limit=1)
    s2_25 = env["university.semester"].search([("academic_year_id", "=", y25.id), ("semester_type", "=", "semester_2")], limit=1)

    y26 = env["university.academic.year"].search([("name", "ilike", "2026-2027")], limit=1)
    s1_26 = env["university.semester"].search([("academic_year_id", "=", y26.id), ("semester_type", "=", "semester_1")], limit=1)
    s2_26 = env["university.semester"].search([("academic_year_id", "=", y26.id), ("semester_type", "=", "semester_2")], limit=1)

    print("\n=== 2. SEED SEMESTER SUBJECT OFFERINGS ===")
    cur_lines = env["university.curriculum.line"].search([])
    sem1_subjs = env["university.subject"].browse(list(set(l.subject_id.id for l in cur_lines if str(l.semester_number) == "1" and l.subject_id)))
    sem2_subjs = env["university.subject"].browse(list(set(l.subject_id.id for l in cur_lines if str(l.semester_number) == "2" and l.subject_id)))

    # Ensure all semesters have full subject offerings
    semester_targets = [
        (s1_24, sem1_subjs),
        (s2_24, sem2_subjs),
        (s1_25, sem1_subjs),
        (s2_25, sem2_subjs),
        (s1_26, sem1_subjs),
        (s2_26, sem2_subjs),
    ]

    total_off_created = 0
    for sem, subjs in semester_targets:
        if not sem:
            continue
        existing_sub_ids = set(env["university.semester.subject"].search([("semester_id", "=", sem.id)]).mapped("subject_id.id"))
        missing_subjs = subjs.filtered(lambda s: s.id not in existing_sub_ids)
        to_create = []
        for s in missing_subjs:
            to_create.append({
                "semester_id": sem.id,
                "academic_year_id": sem.academic_year_id.id,
                "subject_id": s.id,
                "credits": s.credits or 3,
            })
        if to_create:
            env["university.semester.subject"].create(to_create)
            total_off_created += len(to_create)
            print(f"  Added {len(to_create)} offerings to {sem.name} ({sem.academic_year_id.name})")

    print(f"Total new semester offerings created: {total_off_created}")

    print("\n=== 3. SEED CLASS SECTIONS, TIMETABLE SLOTS & ENROLLMENTS ===")
    teachers = env["university.teacher"].search([("active", "=", True)])
    classrooms = env["university.classroom"].search([("active", "=", True)])
    students = env["university.student"].search([("active", "=", True), ("status", "=", "active")])

    semesters_needing_data = [
        (s1_24, "2024-10-07"),
        (s2_24, "2025-03-03"),
        (s2_25, "2026-03-02"),
        (s2_26, "2027-03-01"),
    ]

    timeslot_patterns = [
        ("08:00:00", "09:30:00"),
        ("10:00:00", "11:30:00"),
        ("13:30:00", "15:00:00"),
        ("15:30:00", "17:00:00"),
    ]

    sections_created = 0
    slots_created = 0
    enrollments_created = 0

    for sem, monday_date_str in semesters_needing_data:
        if not sem:
            continue
        existing_secs = env["university.class.section"].search([("semester_id", "=", sem.id)])
        if len(existing_secs) >= 15:
            print(f"  {sem.name} ({sem.academic_year_id.name}) already has {len(existing_secs)} sections.")
            continue

        target_subjs = sem1_subjs if sem.semester_type == "semester_1" else sem2_subjs
        selected_subjs = target_subjs[:20]
        
        base_monday = datetime.date.fromisoformat(monday_date_str)
        
        for idx, subj in enumerate(selected_subjs):
            # Ensure subject has a teacher assigned
            if subj.teacher_ids:
                t = subj.teacher_ids[0]
            else:
                t = teachers[idx % len(teachers)]
                subj.write({"teacher_ids": [(4, t.id)]})

            c = classrooms[idx % len(classrooms)]
            sec_name = f"{subj.code or 'SUB'}-SEC01"
            
            # Check or create section
            sec = env["university.class.section"].search([
                ("name", "=", sec_name),
                ("semester_id", "=", sem.id),
            ], limit=1)
            if not sec:
                sec = env["university.class.section"].create({
                    "name": sec_name,
                    "subject_id": subj.id,
                    "teacher_id": t.id,
                    "classroom_id": c.id,
                    "semester_id": sem.id,
                    "academic_year_id": sem.academic_year_id.id,
                    "capacity": 40,
                    "year_level": "1" if "10" in (subj.code or "") else ("2" if "20" in (subj.code or "") else "3"),
                })
                sections_created += 1

            # Create 2 timetable sessions (Monday & Wednesday OR Tuesday & Thursday)
            day_offset_1 = (idx % 2) # 0=Mon, 1=Tue
            day_offset_2 = day_offset_1 + 2 # Wed or Thu
            time_start_str, time_end_str = timeslot_patterns[idx % len(timeslot_patterns)]

            date_1 = base_monday + datetime.timedelta(days=day_offset_1)
            date_2 = base_monday + datetime.timedelta(days=day_offset_2)

            for d in (date_1, date_2):
                st = datetime.datetime.combine(d, datetime.time.fromisoformat(time_start_str))
                et = datetime.datetime.combine(d, datetime.time.fromisoformat(time_end_str))
                existing_slot = env["university.timetable.slot"].search([
                    ("section_id", "=", sec.id),
                    ("start_time", "=", st),
                ], limit=1)
                if not existing_slot:
                    env["university.timetable.slot"].with_context(skip_conflict_check=True).create({
                        "name": f"{sec.name}-{subj.name} ({d})",
                        "section_id": sec.id,
                        "subject_id": subj.id,
                        "teacher_id": t.id,
                        "classroom_id": c.id,
                        "start_time": st,
                        "end_time": et,
                        "state": "scheduled",
                    })
                    slots_created += 1

            # Enroll 3-5 matching students
            enr_students = students[(idx * 3) % len(students): (idx * 3 + 5) % len(students)]
            if not enr_students:
                enr_students = students[:4]
            for stu in enr_students:
                existing_enr = env["university.enrollment"].search([
                    ("student_id", "=", stu.id),
                    ("class_section_id", "=", sec.id),
                ], limit=1)
                if not existing_enr:
                    env["university.enrollment"].create({
                        "student_id": stu.id,
                        "class_section_id": sec.id,
                        "status": "enrolled",
                        "enrollment_date": sem.date_start,
                    })
                    enrollments_created += 1

        print(f"  Populated {sem.name} ({sem.academic_year_id.name}) with sections, slots, and enrollments.")

    cr.commit()
    print(f"\nCOMPLETED SUCCESSFULLY:")
    print(f" - New Sections Created: {sections_created}")
    print(f" - New Timetable Slots: {slots_created}")
    print(f" - New Enrollments: {enrollments_created}")
