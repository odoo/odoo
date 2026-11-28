import os
import sys
import datetime
import random
import base64
import pytz

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID, fields

DUMMY_PDF_BASE64 = base64.b64encode(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF").decode("ascii")

def run():
    odoo.tools.config.parse_config(['-c', 'odoo.conf', '-d', 'odoo'])
    registry = Registry('odoo')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        print("=== COMPREHENSIVE ACADEMIC STAFF & ECOSYSTEM ENRICHMENT ===")

        Teacher = env['university.teacher']
        Faculty = env['university.faculty']
        Department = env['university.department']
        Assignment = env['university.academic.assignment']
        Section = env['university.class.section']
        Slot = env['university.timetable.slot']
        Attendance = env['university.staff.attendance']
        Classroom = env['university.classroom']
        Timeslot = env['university.timeslot']
        Semester = env['university.semester']

        today = fields.Date.context_today(Teacher)
        sem1 = Semester.search([('semester_type', '=', 'semester_1'), ('academic_year_id.name', 'ilike', '2026')], limit=1)
        if not sem1:
            sem1 = Semester.search([('active', '=', True)], limit=1)

        # -------------------------------------------------------------
        # STEP 1: Enrich Teacher Profiles (Positions, Credentials, Docs)
        # -------------------------------------------------------------
        print("\n1. Enriching Academic Staff Profiles & Documentation...")
        all_teachers = Teacher.search([])
        print(f"Total Academic Staff: {len(all_teachers)}")

        specializations_map = {
            "marketing": ("Brand Identity & Strategic Marketing", "Ph.D. in Marketing, UC Berkeley"),
            "logistics": ("Supply Chain Analytics & Global Logistics", "Ph.D. in Operations Research, MIT"),
            "finance": ("Asset Pricing & Portfolio Optimization", "Ph.D. in Financial Economics, University of Chicago"),
            "management": ("Strategic Leadership & Disruptive Innovation", "Doctor of Business Administration (DBA), Stanford Graduate School of Business"),
            "computer science": ("Algorithms & Distributed Systems", "Ph.D. in Computer Science, Stanford University"),
            "software engineering": ("Software Architecture & Design Patterns", "Ph.D. in Software Engineering, Carnegie Mellon University"),
            "artificial intelligence": ("Deep Learning & Neural Architectures", "Ph.D. in Artificial Intelligence, University of Toronto"),
            "electrical engineering": ("Power Systems & Digital Signal Processing", "Ph.D. in Electrical Engineering, Caltech"),
            "clinical medicine": ("Internal Medicine & Diagnostic Pathology", "Doctor of Medicine (M.D.), Johns Hopkins University"),
            "nursing": ("Clinical Care & Public Health Epidemiology", "Ph.D. in Nursing Sciences, Columbia University"),
        }

        for t in all_teachers:
            vals = {}
            t_name_lower = (t.name or "").lower()
            dept_name_lower = (t.department_id.name or "").lower()

            # Set position if missing
            if not t.position:
                if any(x in t_name_lower for x in ["aaker", "ng", "christensen", "knuth", "turing", "fowler", "brooks", "graham", "porter", "drucker", "kotler", "nightingale", "curie"]):
                    vals['position'] = 'professor'
                    if not t.title:
                        vals['title'] = 'prof'
                elif any(x in t_name_lower for x in ["hassabis", "fama", "torvalds", "scholes", "farmer", "osler", "liskov", "lovelace", "hopper", "mintzberg"]):
                    vals['position'] = 'associate_professor'
                    if not t.title:
                        vals['title'] = 'dr'
                elif any(x in t_name_lower for x in ["christopher", "miller", "benner", "seacole", "faraday", "maxwell", "tesla"]):
                    vals['position'] = 'assistant_professor'
                    if not t.title:
                        vals['title'] = 'dr'
                else:
                    vals['position'] = 'lecturer'

            # Match specialization & qualification based on department
            matched_spec = False
            for k, (spec, qual) in specializations_map.items():
                if k in dept_name_lower:
                    matched_spec = (spec, qual)
                    break
            if not matched_spec:
                matched_spec = ("Advanced Academic Instruction & Research", "Ph.D. in Academic Discipline")

            if not t.specialization:
                vals['specialization'] = matched_spec[0]
            if not t.qualification:
                vals['qualification'] = matched_spec[1]
            if not t.hire_date:
                vals['hire_date'] = datetime.date(2021, 9, 1)

            # Documentation & Credentials
            safe_name = (t.name or "Faculty").replace(" ", "_").replace(".", "")
            vals.update({
                'doc_verification_status': 'verified',
                'verification_date': datetime.date(2026, 1, 15),
                'verified_by': SUPERUSER_ID,
                'resume_filename': f"{safe_name}_Curriculum_Vitae.pdf",
                'resume_file': DUMMY_PDF_BASE64,
                'degree_filename': f"{safe_name}_Doctoral_Diploma.pdf",
                'degree_file': DUMMY_PDF_BASE64,
                'contract_filename': f"{safe_name}_Faculty_Employment_Contract.pdf",
                'contract_file': DUMMY_PDF_BASE64,
                'id_card_filename': f"{safe_name}_National_ID_Passport.pdf",
                'id_card_file': DUMMY_PDF_BASE64,
                'research_interests': f"Leading scholarly inquiries in {vals.get('specialization', t.specialization or matched_spec[0])}, curriculum modernizations, and industry academic partnership.",
                'publications_summary': "Over 18 peer-reviewed research publications, 4 books and book chapters, multiple patent grants, and senior member of international scholarly associations.",
                'notes': f"Senior academic staff member for {t.department_id.name or 'University'}. Full credentials, doctoral diplomas, research ethics compliance, and university appointment verified.",
            })

            t.write(vals)

        print(f"  + Successfully updated credentials and document repositories for {len(all_teachers)} staff members.")

        # -------------------------------------------------------------
        # STEP 2: University Leadership & Role Assignments (Deans & HODs)
        # -------------------------------------------------------------
        print("\n2. Configuring University Leadership Role Assignments...")

        # A. Heads of Department (HOD)
        hod_configs = [
            ("Department of Marketing & Logistics", "David Aaker"),
            ("Department of Management & Strategy", "Clayton Christensen"),
            ("Department of Finance & Accounting", "Benjamin Graham"),
            ("Department of Software Engineering", "Martin Fowler"),
            ("Department of Artificial Intelligence & Data Science", "Andrew Ng"),
            ("Department of Computer Science", "Alan Turing"),
            ("Department of Electrical Engineering", "Nikola Tesla"),
            ("Department of Nursing & Public Health", "Florence Nightingale"),
            ("Department of Clinical Medicine", "Dr. Sarah Jenkins"),
        ]

        active_hods_created = 0
        for dept_name, teacher_name_kw in hod_configs:
            dept = Department.search([('name', '=', dept_name)], limit=1)
            if not dept:
                continue
            existing_hod = Assignment.search([('department_id', '=', dept.id), ('role', '=', 'department_head'), ('active', '=', True)], limit=1)
            if not existing_hod:
                teacher = Teacher.search([('department_id', '=', dept.id), ('name', 'ilike', teacher_name_kw)], limit=1)
                if not teacher:
                    teacher = Teacher.search([('department_id', '=', dept.id)], limit=1)
                if teacher:
                    asg = Assignment.create({
                        'staff_id': teacher.id,
                        'role': 'department_head',
                        'department_id': dept.id,
                        'start_date': datetime.date(2026, 1, 1),
                        'active': True,
                        'notes': f"Official appointment as Head of {dept.name}.",
                    })
                    active_hods_created += 1
                    print(f"  + HOD Appointed: {teacher.name} -> {dept.name}")

        # B. Heads of Faculty (Deans)
        dean_configs = [
            ("Faculty of Business Administration & Management", "Philip Kotler"),
            ("Faculty of Computer Science & Information Technology", "Donald Knuth"),
            ("Faculty of Health Sciences & Medicine", "William Osler"),
            ("Faculty of Engineering & Technology", "Charles Xavier"),
            ("Faculty of Medicine & Health Sciences", "Dr. Sarah Jenkins"),
        ]

        active_deans_created = 0
        for fac_name, teacher_name_kw in dean_configs:
            fac = Faculty.search([('name', '=', fac_name)], limit=1)
            if not fac:
                continue
            existing_dean = Assignment.search([('faculty_id', '=', fac.id), ('role', '=', 'dean'), ('active', '=', True)], limit=1)
            if not existing_dean:
                teacher = Teacher.search([('faculty_id', '=', fac.id), ('name', 'ilike', teacher_name_kw)], limit=1)
                if not teacher:
                    teacher = Teacher.search([('faculty_id', '=', fac.id)], limit=1)
                if teacher:
                    asg = Assignment.create({
                        'staff_id': teacher.id,
                        'role': 'dean',
                        'faculty_id': fac.id,
                        'start_date': datetime.date(2026, 1, 1),
                        'active': True,
                        'notes': f"Executive academic appointment as Dean of {fac.name}.",
                    })
                    active_deans_created += 1
                    print(f"  + Dean Appointed: {teacher.name} -> {fac.name}")

        # Recompute admin roles across all teachers
        all_teachers._compute_is_head()
        all_teachers._compute_admin_roles()
        all_teachers._compute_managed_scopes()
        all_teachers._compute_admin_appointments()

        # -------------------------------------------------------------
        # STEP 3: Generate Timetable Sessions for Academic Staff
        # -------------------------------------------------------------
        print("\n3. Generating Timetable Sessions for Class Sections & Teachers...")

        all_classrooms = Classroom.search([('status', '=', 'active')])
        if not all_classrooms:
            all_classrooms = Classroom.search([])

        # Timeslot schedule patterns (Mon/Wed: days 0 and 2; Tue/Thu: days 1 and 3)
        schedule_patterns = [
            (0, 8.0, 9.5),   # Mon 08:00 - 09:30
            (0, 10.0, 11.5), # Mon 10:00 - 11:30
            (0, 13.5, 15.0), # Mon 13:30 - 15:00
            (1, 8.0, 9.5),   # Tue 08:00 - 09:30
            (1, 10.0, 11.5), # Tue 10:00 - 11:30
            (1, 13.5, 15.0), # Tue 13:30 - 15:00
            (2, 8.0, 9.5),   # Wed 08:00 - 09:30
            (2, 10.0, 11.5), # Wed 10:00 - 11:30
            (2, 13.5, 15.0), # Wed 13:30 - 15:00
            (3, 8.0, 9.5),   # Thu 08:00 - 09:30
            (3, 10.0, 11.5), # Thu 10:00 - 11:30
            (3, 13.5, 15.0), # Thu 13:30 - 15:00
            (4, 8.0, 9.5),   # Fri 08:00 - 09:30
            (4, 10.0, 11.5), # Fri 10:00 - 11:30
        ]

        # Target academic week in current term (e.g. Current week)
        user_tz = pytz.timezone(env.user.tz or 'UTC')
        now_dt = datetime.datetime.now(user_tz)
        today_date = now_dt.date()
        monday_date = today_date - datetime.timedelta(days=today_date.weekday())

        sections_to_schedule = Section.search([('active', '=', True)])
        created_slots = 0

        for sec_idx, sec in enumerate(sections_to_schedule):
            teacher = sec.teacher_id
            if not teacher:
                continue

            # Check existing slots for this section
            existing_slots = Slot.search([('section_id', '=', sec.id), ('state', '!=', 'cancelled')])
            if not existing_slots:
                # Schedule 2 weekly sessions for this class section (e.g. pattern_idx and pattern_idx+6)
                pat_1 = schedule_patterns[sec_idx % len(schedule_patterns)]
                pat_2 = schedule_patterns[(sec_idx + 6) % len(schedule_patterns)]

                room = sec.classroom_id or all_classrooms[sec_idx % len(all_classrooms)]

                for dow, sh, eh in [pat_1, pat_2]:
                    sess_date = monday_date + datetime.timedelta(days=dow)
                    s_h, s_m = int(sh), int(round((sh - int(sh)) * 60))
                    e_h, e_m = int(eh), int(round((eh - int(eh)) * 60))

                    local_start = datetime.datetime.combine(sess_date, datetime.time(s_h, s_m))
                    local_end = datetime.datetime.combine(sess_date, datetime.time(e_h, e_m))

                    utc_start = user_tz.localize(local_start).astimezone(pytz.utc).replace(tzinfo=None)
                    utc_end = user_tz.localize(local_end).astimezone(pytz.utc).replace(tzinfo=None)

                    # Check conflict for teacher
                    conflict = Slot.search([
                        ('state', '!=', 'cancelled'),
                        ('teacher_id', '=', teacher.id),
                        ('start_time', '<', utc_end),
                        ('end_time', '>', utc_start),
                    ], limit=1)

                    if not conflict:
                        # Find matching timeslot record
                        ts_rec = Timeslot.search([('day_of_week', '=', str(dow)), ('start_hour', '=', sh)], limit=1)

                        slot = Slot.with_context(skip_term_range_check=True, skip_conflict_check=True).create({
                            'name': f"{sec.name}-{sec.subject_id.code if sec.subject_id else 'CLS'} ({sess_date})",
                            'section_id': sec.id,
                            'subject_id': sec.subject_id.id if sec.subject_id else False,
                            'teacher_id': teacher.id,
                            'classroom_id': room.id if room else False,
                            'timeslot_id': ts_rec.id if ts_rec else False,
                            'start_time': utc_start,
                            'end_time': utc_end,
                            'date': sess_date,
                            'state': 'scheduled',
                            'generation_state': 'published',
                            'session_type': 'lecture',
                            'location': room.name if room else 'Academic Hall',
                            'allow_on_holiday': True,
                            'holiday_override_reason': 'Authorized academic session approved by Academic Affairs Directorate',
                        })
                        created_slots += 1

        all_teachers._compute_teaching_stats()
        print(f"  + Generated {created_slots} new timetable sessions. Total timetable slots now: {Slot.search_count([])}")

        # -------------------------------------------------------------
        # STEP 4: Seed Rich Attendance Logs for Academic Staff
        # -------------------------------------------------------------
        print("\n4. Seeding Staff Attendance Records across Working Days...")

        # Past 20 working days up to today
        working_days = []
        d = today_date - datetime.timedelta(days=28)
        while d <= today_date:
            if d.weekday() < 5:  # Monday to Friday
                working_days.append(d)
            d += datetime.timedelta(days=1)

        print(f"Targeting {len(working_days)} working days for {len(all_teachers)} teachers...")

        remarks_present = [
            "Full academic workday - delivered morning lecture and held afternoon office consultations.",
            "Attended departmental faculty board and conducted laboratory supervision.",
            "Normal working hours - curriculum review and undergraduate research mentoring.",
            "Lectures conducted on schedule, student advisement office hours completed.",
            "Participated in university academic senate committee and held student advising.",
            "Full day presence - proctored midterm assessments and finalized semester grading rubrics.",
        ]

        remarks_late = [
            "Late check-in due to morning inter-campus transit delay; full makeup hours completed.",
            "Late arrival due to morning emergency student thesis advisement session.",
            "Slight check-in delay due to faculty entrance card reader maintenance.",
        ]

        remarks_duty = [
            "Official University Duty - representing faculty at National Higher Education Symposium.",
            "Official Duty - external thesis evaluation board and university research council.",
        ]

        created_att = 0
        for teacher in all_teachers:
            for day in working_days:
                existing = Attendance.search([('staff_id', '=', teacher.id), ('date', '=', day)], limit=1)
                if not existing:
                    # Random scenario for realism: 90% present, 5% late, 3% official duty, 2% leave
                    rand_val = random.random()
                    if rand_val < 0.90:
                        status = 'present'
                        check_in_m = random.randint(5, 25)
                        check_out_m = random.randint(10, 45)
                        check_in_dt = datetime.datetime.combine(day, datetime.time(8, check_in_m))
                        check_out_dt = datetime.datetime.combine(day, datetime.time(17, check_out_m))
                        worked_hours = round((check_out_dt - check_in_dt).total_seconds() / 3600.0, 2)
                        remark = random.choice(remarks_present)
                    elif rand_val < 0.95:
                        status = 'late'
                        check_in_dt = datetime.datetime.combine(day, datetime.time(9, random.randint(15, 35)))
                        check_out_dt = datetime.datetime.combine(day, datetime.time(18, 0))
                        worked_hours = round((check_out_dt - check_in_dt).total_seconds() / 3600.0, 2)
                        remark = random.choice(remarks_late)
                    elif rand_val < 0.98:
                        status = 'official_duty'
                        check_in_dt = datetime.datetime.combine(day, datetime.time(8, 30))
                        check_out_dt = datetime.datetime.combine(day, datetime.time(17, 30))
                        worked_hours = 9.0
                        remark = random.choice(remarks_duty)
                    else:
                        status = 'leave'
                        check_in_dt = False
                        check_out_dt = False
                        worked_hours = 0.0
                        remark = "Approved personal leave."

                    # Convert check_in and check_out to UTC
                    utc_cin = user_tz.localize(check_in_dt).astimezone(pytz.utc).replace(tzinfo=None) if check_in_dt else False
                    utc_cout = user_tz.localize(check_out_dt).astimezone(pytz.utc).replace(tzinfo=None) if check_out_dt else False

                    Attendance.create({
                        'staff_id': teacher.id,
                        'date': day,
                        'check_in': utc_cin,
                        'check_out': utc_cout,
                        'worked_hours': worked_hours,
                        'status': status,
                        'state': 'approved',
                        'remark': remark,
                    })
                    created_att += 1

        all_teachers._compute_presence()
        print(f"  + Created {created_att} staff attendance records. Total attendance records now: {Attendance.search_count([])}")

        cr.commit()

        # -------------------------------------------------------------
        # STEP 5: Verification & Inspection
        # -------------------------------------------------------------
        print("\n===========================================================")
        print(">>> ACADEMIC STAFF & ECOSYSTEM SEEDING SUMMARY <<<")
        print(f"Total Academic Staff: {len(Teacher.search([]))}")
        print(f"Staff with Timetable Sessions: {len(Teacher.search([]).filtered(lambda t: len(t.timetable_slot_ids) > 0))} / {len(Teacher.search([]))}")
        print(f"Staff with Attendance Logs: {len(Teacher.search([]).filtered(lambda t: len(t.attendance_ids) > 0))} / {len(Teacher.search([]))}")
        print(f"Staff with Role Assignments: {len(Teacher.search([]).filtered(lambda t: len(t.assignment_ids) > 0))}")
        print(f"Total Active Deans: {Assignment.search_count([('role', '=', 'dean'), ('active', '=', True)])}")
        print(f"Total Active HODs: {Assignment.search_count([('role', '=', 'department_head'), ('active', '=', True)])}")
        print(f"Total Staff Attendance Records: {Attendance.search_count([])}")
        print(f"Total Timetable Slots: {Slot.search_count([])}")

        d_aaker = Teacher.search([('name', 'ilike', 'Aaker')], limit=1)
        if d_aaker:
            print(f"\nVerification for Prof. David Aaker (T-MKT03):")
            print(f"  Title & Display Name: {d_aaker.display_name}")
            print(f"  Position: {d_aaker.position}")
            print(f"  Specialization: {d_aaker.specialization}")
            print(f"  Qualification: {d_aaker.qualification}")
            print(f"  Is HOD: {d_aaker.is_hod} (Managed Dept: {d_aaker.managed_department_id.name})")
            print(f"  HOD Appointment Start: {d_aaker.hod_appointment_start}")
            print(f"  Role Assignments Count: {len(d_aaker.assignment_ids)}")
            print(f"  Class Sections Count: {len(d_aaker.section_ids)}")
            print(f"  Timetable Sessions Count: {len(d_aaker.timetable_slot_ids)}")
            print(f"  Weekly Hours: {d_aaker.weekly_hours} h/w")
            print(f"  Attendance Records Count: {len(d_aaker.attendance_ids)}")
            print(f"  Document Verification Status: {d_aaker.doc_verification_status}")
            print(f"  CV Attached: {bool(d_aaker.resume_file)} ({d_aaker.resume_filename})")
            print(f"  Diploma Attached: {bool(d_aaker.degree_file)} ({d_aaker.degree_filename})")
            print(f"  Contract Attached: {bool(d_aaker.contract_file)} ({d_aaker.contract_filename})")
        print("===========================================================")

if __name__ == '__main__':
    run()
