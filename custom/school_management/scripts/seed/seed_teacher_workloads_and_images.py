import os
import sys
import datetime
import base64
import io
import random
from PIL import Image, ImageDraw, ImageFont

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

def create_gradient_avatar(initials, bg_color1, bg_color2, size=320):
    img = Image.new("RGBA", (size, size), bg_color1)
    draw = ImageDraw.Draw(img)
    for y in range(size):
        r = int(bg_color1[0] + (bg_color2[0] - bg_color1[0]) * (y / size))
        g = int(bg_color1[1] + (bg_color2[1] - bg_color1[1]) * (y / size))
        b = int(bg_color1[2] + (bg_color2[2] - bg_color1[2]) * (y / size))
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    margin = 20
    draw.ellipse([(margin, margin), (size - margin, size - margin)], outline=(255, 255, 255, 120), width=3)
    inner_margin = 35
    draw.ellipse([(inner_margin, inner_margin), (size - inner_margin, size - inner_margin)], fill=(255, 255, 255, 45))
    try:
        font = ImageFont.truetype("arial.ttf", 90)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), initials, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((size - w) / 2, (size - h) / 2 - 10), initials, fill=(255, 255, 255, 250), font=font)
    draw.rounded_rectangle([(size/4, size - 50), (size*3/4, size - 22)], radius=8, fill=(255, 255, 255, 220))
    try:
        sub_font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        sub_font = ImageFont.load_default()
    badge_text = "FACULTY"
    s_bbox = draw.textbbox((0, 0), badge_text, font=sub_font)
    sw = s_bbox[2] - s_bbox[0]
    draw.text(((size - sw) / 2, size - 44), badge_text, fill=(30, 41, 59), font=sub_font)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def create_department_cover(code, name, bg_color1, bg_color2, width=640, height=360):
    img = Image.new("RGBA", (width, height), bg_color1)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(bg_color1[0] + (bg_color2[0] - bg_color1[0]) * (y / height))
        g = int(bg_color1[1] + (bg_color2[1] - bg_color1[1]) * (y / height))
        b = int(bg_color1[2] + (bg_color2[2] - bg_color1[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    draw.ellipse([(width - 160, -60), (width + 120, 220)], fill=(255, 255, 255, 20))
    draw.ellipse([(-80, height - 180), (140, height + 40)], fill=(255, 255, 255, 15))
    draw.rectangle([(0, height - 8), (width, height)], fill=(255, 255, 255, 180))
    draw.rounded_rectangle([(40, 40), (160, 85)], radius=12, fill=(255, 255, 255, 50), outline=(255, 255, 255, 180), width=2)
    try:
        font_code = ImageFont.truetype("arialbd.ttf", 26)
    except Exception:
        font_code = ImageFont.load_default()
    c_bbox = draw.textbbox((0, 0), code, font=font_code)
    cw = c_bbox[2] - c_bbox[0]
    draw.text((40 + (120 - cw)/2, 48), code, fill=(255, 255, 255, 255), font=font_code)
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 28)
        font_sub = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_title = font_sub = ImageFont.load_default()
    words = name.split()
    line1 = []
    line2 = []
    for w in words:
        if len(" ".join(line1 + [w])) <= 28:
            line1.append(w)
        else:
            line2.append(w)
    text_line1 = " ".join(line1)
    text_line2 = " ".join(line2)
    draw.text((40, 150), text_line1, fill=(255, 255, 255, 255), font=font_title)
    if text_line2:
        draw.text((40, 190), text_line2, fill=(255, 255, 255, 240), font=font_title)
    draw.text((40, 260), "DEPARTMENT OF ACADEMIC EXCELLENCE", fill=(255, 255, 255, 180), font=font_sub)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def create_classroom_cover(room_name, room_type, capacity, bg_color1, bg_color2, width=640, height=360):
    img = Image.new("RGBA", (width, height), bg_color1)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(bg_color1[0] + (bg_color2[0] - bg_color1[0]) * (y / height))
        g = int(bg_color1[1] + (bg_color2[1] - bg_color1[1]) * (y / height))
        b = int(bg_color1[2] + (bg_color2[2] - bg_color1[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    for x in range(0, width, 50):
        draw.line([(x, 0), (x + 100, height)], fill=(255, 255, 255, 12), width=1)
    cap_text = f"Capacity: {capacity} Seats"
    try:
        f_cap = ImageFont.truetype("arialbd.ttf", 18)
        f_name = ImageFont.truetype("arialbd.ttf", 32)
        f_type = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        f_cap = f_name = f_type = ImageFont.load_default()
    draw.rounded_rectangle([(40, 40), (230, 80)], radius=20, fill=(15, 23, 42, 160), outline=(255, 255, 255, 120), width=1)
    draw.text((58, 49), cap_text, fill=(255, 255, 255, 250), font=f_cap)
    draw.text((40, 160), room_name, fill=(255, 255, 255, 255), font=f_name)
    draw.text((40, 215), f"FACILITY TYPE: {room_type.upper()}", fill=(226, 232, 240, 210), font=f_type)
    draw.ellipse([(40, 280), (56, 296)], fill=(34, 197, 94))
    draw.text((68, 278), "Active Academic Resource", fill=(241, 245, 249), font=f_cap)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def create_academic_year_cover(year_name, is_current, width=640, height=360):
    bg_color1 = (15, 23, 42) if not is_current else (24, 49, 83)
    bg_color2 = (30, 41, 59) if not is_current else (14, 116, 144)
    img = Image.new("RGBA", (width, height), bg_color1)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(bg_color1[0] + (bg_color2[0] - bg_color1[0]) * (y / height))
        g = int(bg_color1[1] + (bg_color2[1] - bg_color1[1]) * (y / height))
        b = int(bg_color1[2] + (bg_color2[2] - bg_color1[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    draw.ellipse([(width - 200, -80), (width + 100, 220)], outline=(255, 255, 255, 25), width=2)
    draw.ellipse([(width - 240, -120), (width + 140, 260)], outline=(255, 255, 255, 15), width=2)
    try:
        f_badge = ImageFont.truetype("arialbd.ttf", 16)
        f_year = ImageFont.truetype("arialbd.ttf", 46)
        f_sub = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        f_badge = f_year = f_sub = ImageFont.load_default()
    badge_label = "CURRENT ACTIVE SESSION" if is_current else "ACADEMIC CYCLE"
    badge_color = (16, 185, 129) if is_current else (100, 116, 139)
    draw.rounded_rectangle([(40, 40), (290, 80)], radius=20, fill=badge_color)
    draw.text((55, 51), badge_label, fill=(255, 255, 255), font=f_badge)
    draw.text((40, 140), "Academic Year", fill=(148, 163, 184), font=f_sub)
    draw.text((40, 180), year_name, fill=(255, 255, 255), font=f_year)
    draw.text((40, 260), "University Calendar & Course Registry", fill=(203, 213, 225), font=f_sub)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def schedule_conflict_free_session(env, section, subject_id, teacher_id, preferred_room, all_rooms, all_timeslots, base_monday_dates):
    """Finds a guaranteed collision-free (timeslot, date, room) and creates the slot."""
    # Try room priority: preferred_room first, then all other available rooms
    candidate_rooms = [preferred_room] + [r for r in all_rooms if r.id != preferred_room.id]
    
    for monday in base_monday_dates:
        for ts in all_timeslots:
            day_offset = int(ts.day_of_week)
            session_date = monday + datetime.timedelta(days=day_offset)
            start_hour = int(ts.start_hour)
            start_min = int(round((ts.start_hour % 1) * 60))
            end_hour = int(ts.end_hour)
            end_min = int(round((ts.end_hour % 1) * 60))
            
            start_dt = datetime.datetime.combine(session_date, datetime.time(start_hour, start_min))
            end_dt = datetime.datetime.combine(session_date, datetime.time(end_hour, end_min))
            
            # Check teacher conflict
            overlap_domain = [
                ("state", "!=", "cancelled"),
                ("start_time", "<", end_dt),
                ("end_time", ">", start_dt),
            ]
            if env['university.timetable.slot'].search_count(overlap_domain + [('teacher_id', '=', teacher_id)]):
                continue
            if env['university.timetable.slot'].search_count(overlap_domain + [('section_id', '=', section.id)]):
                continue
                
            for room in candidate_rooms:
                if room.status != 'available':
                    continue
                if env['university.timetable.slot'].search_count(overlap_domain + [('classroom_id', '=', room.id)]):
                    continue
                    
                # Both teacher and room are completely free!
                slot = env['university.timetable.slot'].create({
                    'section_id': section.id,
                    'subject_id': subject_id,
                    'teacher_id': teacher_id,
                    'classroom_id': room.id,
                    'timeslot_id': ts.id,
                    'start_time': start_dt,
                    'end_time': end_dt,
                    'state': 'published',
                    'generation_state': 'published',
                })
                return slot
    return None


def main():
    print("=== SEEDING TEACHER WORKLOADS, SUBJECT MATCHES & HIGH-RES IMAGES ===")
    odoo.tools.config.parse_config(["-c", "odoo.conf", "-d", "odoo"])
    registry = Registry("odoo")
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # 0. Ensure classroom statuses are all available
        all_rooms = env['university.classroom'].search([])
        for r in all_rooms:
            if r.status != 'available':
                r.status = 'available'
                print(f"Set room {r.name} to available.")
        
        # 1. ACADEMIC YEAR & SEMESTER
        academic_year = env['university.academic.year'].search([('current', '=', True)], limit=1)
        if not academic_year:
            academic_year = env['university.academic.year'].search([], order='date_start desc', limit=1)
        semester = env['university.semester'].search([
            ('academic_year_id', '=', academic_year.id),
            ('active', '=', True)
        ], limit=1)
        if not semester:
            semester = env['university.semester'].search([], limit=1)
            
        print(f"Academic Year: {academic_year.name} (id={academic_year.id}), Semester: {semester.name} (id={semester.id})")
        
        teacher_configs = [
            {
                "id": 2061,
                "name": "Grace Hopper",
                "specialization": "Software Architecture, Compilers & Automated QA Testing",
                "department_id": 4756, # Software Engineering
                "subjects": [1334, 1333], # CS307, CS306
                "classroom_name": "Software Engineering Lab 202",
                "section_names": [
                    ("CS307-A", "CS307 - Software Quality Assurance & Testing (Sec A)"),
                    ("CS306-B", "CS306 - Full-Stack Enterprise Architecture (Sec B)")
                ]
            },
            {
                "id": 2103,
                "name": "Yann Lecun",
                "specialization": "Deep Learning, Convolutional Neural Networks & Machine Vision",
                "department_id": 4757, # AI & Data Science
                "subjects": [1337, 1329], # CS401, CS303
                "classroom_name": "AI & Robotics Lab 201",
                "section_names": [
                    ("CS401-A", "CS401 - Deep Learning & Computer Vision (Sec A)"),
                    ("CS303-AI-B", "CS303 - Artificial Intelligence & Machine Learning (Sec B)")
                ]
            },
            {
                "id": 502,
                "name": "Meng lay",
                "specialization": "Strategic Management, Organizational Behavior & Agile Leadership",
                "department_id": 4758, # Management & Strategy
                "subjects": [1346, 1350], # MGT101, MGT102
                "classroom_name": "Business Lecture Hall 301",
                "section_names": [
                    ("MGT101-A", "MGT101 - Principles of Management (Sec A)"),
                    ("MGT102-B", "MGT102 - Organizational Behavior & Leadership (Sec B)")
                ]
            },
            {
                "id": 437,
                "name": "Dr. Rich",
                "specialization": "Human Physiology, Internal Medicine & Clinical Diagnostics",
                "department_id": 9, # Clinical Medicine
                "subjects": [9, 11], # MED102, MED105
                "classroom_name": "General Classroom 102",
                "section_names": [
                    ("MED102-A", "MED102 - Human Physiology I (Sec A)"),
                    ("MED105-B", "MED105 - Introduction to Clinical Medicine (Sec B)")
                ]
            },
            {
                "id": 6,
                "name": "Dr. Sarah Jenkins",
                "specialization": "Clinical Pharmacology, Pharmacokinetics & Molecular Therapeutics",
                "department_id": 9, # Clinical Medicine
                "subjects": [14, 10], # NURS210, MED103
                "classroom_name": "Tech Auditorium 101",
                "section_names": [
                    ("NURS210-A", "NURS210 - Clinical Pharmacology (Sec A)"),
                    ("MED103-B", "MED103 - Medical Biochemistry & Genetics (Sec B)")
                ]
            },
            {
                "id": 3,
                "name": "Dr. John Doe",
                "specialization": "Relational Database Engines, Distributed Big Data & Machine Learning",
                "department_id": 1, # Computer Science
                "subjects": [1, 12], # DBMS, CS303
                "classroom_name": "B201",
                "section_names": [
                    ("DBMS-A", "DBMS - Relational Database Management Systems (Sec A)"),
                    ("CS303-ML", "CS303 - Machine Learning Algorithms & Applications (Sec A)")
                ]
            },
            {
                "id": 5,
                "name": "Mr. Reaksa",
                "specialization": "Computer Systems Architecture, Linux DevOps & Cloud Infrastructure",
                "department_id": 1, # Computer Science
                "subjects": [2, 11], # CA, Devops
                "classroom_name": "Networking & Systems Lab 203",
                "section_names": [
                    ("CA-A", "CA - Computer Architecture & Microprocessors (Sec A)"),
                    ("DEVOPS-A", "DEVOPS - Cloud Architecture & Server Orchestration (Sec A)")
                ]
            }
        ]
        
        all_students = list(env['university.student'].search([('status', '=', 'active')]))
        if not all_students:
            all_students = list(env['university.student'].search([]))
            
        all_timeslots = list(env['university.timeslot'].search([('active', '=', True)]))
        all_classrooms = list(env['university.classroom'].search([('status', '=', 'available')]))
        
        # Candidate schedule weeks
        candidate_mondays = [
            datetime.date(2026, 10, 19),
            datetime.date(2026, 10, 26),
            datetime.date(2026, 11, 2),
            datetime.date(2026, 11, 9),
            datetime.date(2026, 11, 16),
            datetime.date(2026, 11, 23),
        ]
        
        for tcfg in teacher_configs:
            teacher = env['university.teacher'].browse(tcfg["id"])
            if not teacher.exists():
                print(f"Teacher {tcfg['name']} (id={tcfg['id']}) not found, skipping.")
                continue
                
            print(f"\nProcessing teacher: {teacher.name} (id={teacher.id})")
            vals_to_update = {
                'specialization': tcfg["specialization"],
                'department_id': tcfg["department_id"],
                'subject_ids': [(6, 0, tcfg["subjects"])]
            }
            teacher.write(vals_to_update)
            print(f"  Updated profile, department {tcfg['department_id']}, subjects {tcfg['subjects']}")
            
            preferred_room = env['university.classroom'].search([('name', '=', tcfg["classroom_name"])], limit=1)
            if not preferred_room or preferred_room.status != 'available':
                preferred_room = all_classrooms[0] if all_classrooms else False
                
            for idx, (code, sec_name) in enumerate(tcfg["section_names"]):
                subj_id = tcfg["subjects"][idx % len(tcfg["subjects"])]
                subject = env['university.subject'].browse(subj_id)
                program = subject.program_ids[:1] if subject.program_ids else False
                
                sec = env['university.class.section'].search([
                    ('teacher_id', '=', teacher.id),
                    ('subject_id', '=', subj_id),
                    ('semester_id', '=', semester.id)
                ], limit=1)
                
                if not sec:
                    sec = env['university.class.section'].create({
                        'name': sec_name,
                        'teacher_id': teacher.id,
                        'subject_id': subj_id,
                        'program_id': program.id if program else False,
                        'semester_id': semester.id,
                        'classroom_id': preferred_room.id if preferred_room else False,
                        'capacity': 40,
                        'active': True,
                    })
                    print(f"  Created Section: {sec.name} (id={sec.id})")
                else:
                    print(f"  Existing Section: {sec.name} (id={sec.id})")
                    
                # Enroll students
                current_enrolled = env['university.enrollment'].search_count([('class_section_id', '=', sec.id)])
                if current_enrolled < 10 and all_students:
                    sample_students = random.sample(all_students, min(14, len(all_students)))
                    for stu in sample_students:
                        already = env['university.enrollment'].search([
                            ('student_id', '=', stu.id),
                            ('class_section_id', '=', sec.id)
                        ], limit=1)
                        if not already:
                            try:
                                env['university.enrollment'].create({
                                    'student_id': stu.id,
                                    'class_section_id': sec.id,
                                    'status': 'enrolled',
                                })
                            except Exception:
                                pass
                    print(f"  Enrolled students in {sec.name}. Total: {env['university.enrollment'].search_count([('class_section_id', '=', sec.id)])}")
                    
                # Create Timetable sessions without ANY conflict
                current_slots = env['university.timetable.slot'].search_count([('section_id', '=', sec.id)])
                target_slots = 4
                while current_slots < target_slots:
                    slot = schedule_conflict_free_session(
                        env=env,
                        section=sec,
                        subject_id=subj_id,
                        teacher_id=teacher.id,
                        preferred_room=preferred_room,
                        all_rooms=all_classrooms,
                        all_timeslots=all_timeslots,
                        base_monday_dates=candidate_mondays
                    )
                    if slot:
                        current_slots += 1
                    else:
                        print(f"  Warning: could not find conflict-free slot for {sec.name}")
                        break
                print(f"  Timetable sessions for {sec.name}: {current_slots} sessions scheduled.")

        # 3. GENERATE & SEED IMAGES FOR ALL TEACHERS
        print("\n--- Seeding / Updating Teacher Profile Images ---")
        palette_teachers = [
            ((30, 58, 138), (37, 99, 235)),   # Blue
            ((6, 78, 59), (16, 185, 129)),     # Emerald
            ((88, 28, 135), (147, 51, 234)),   # Purple
            ((136, 19, 55), (225, 29, 72)),    # Rose
            ((120, 53, 15), (217, 119, 6)),    # Amber
            ((19, 78, 74), (20, 184, 166)),    # Teal
            ((67, 56, 202), (99, 102, 241)),   # Indigo
        ]
        
        all_teachers = env['university.teacher'].search([])
        for idx, t in enumerate(all_teachers):
            if not t.image_1920:
                clean_name = t.name.replace("Dr.", "").replace("Mr.", "").replace("Ms.", "").strip()
                initials = "".join([part[0].upper() for part in clean_name.split() if part])[:2]
                if not initials:
                    initials = "AC"
                c1, c2 = palette_teachers[idx % len(palette_teachers)]
                img_b64 = create_gradient_avatar(initials, c1, c2)
                t.image_1920 = img_b64
                print(f"  Generated avatar for teacher: {t.name}")
                
        # 4. GENERATE & SEED IMAGES FOR DEPARTMENTS
        print("\n--- Seeding Department Header Images ---")
        dept_palettes = [
            ((15, 23, 42), (30, 41, 59)),     # Dark slate
            ((30, 58, 138), (29, 78, 216)),   # Royal Blue
            ((6, 78, 59), (5, 150, 105)),     # Forest Emerald
            ((124, 45, 18), (234, 88, 12)),   # Warm Orange/Rust
            ((88, 28, 135), (126, 34, 206)),  # Deep Violet
            ((19, 78, 74), (13, 148, 136)),   # Dark Teal
            ((136, 19, 55), (190, 18, 60)),   # Ruby
            ((76, 29, 149), (109, 40, 217)),  # Indigo
            ((17, 24, 39), (55, 65, 81)),     # Charcoal
            ((24, 49, 83), (8, 145, 178)),    # Cyan Tech
            ((67, 56, 202), (79, 70, 229)),   # Bright Indigo
        ]
        
        all_departments = env['university.department'].search([])
        for idx, dept in enumerate(all_departments):
            if not dept.image_1920:
                c1, c2 = dept_palettes[idx % len(dept_palettes)]
                code = dept.code or (dept.name[:4].upper())
                cover_b64 = create_department_cover(code, dept.name, c1, c2)
                dept.image_1920 = cover_b64
                if not dept.color:
                    dept.color = (idx % 11) + 1
                print(f"  Generated cover for department: {dept.name} ({code})")
                
        # 5. GENERATE & SEED IMAGES FOR CLASSROOMS
        print("\n--- Seeding Classroom Visual Cards ---")
        room_palettes = [
            ((24, 49, 83), (14, 116, 144)),   # Cyan lab
            ((30, 41, 59), (51, 65, 85)),     # Sleek slate
            ((6, 78, 59), (16, 185, 129)),    # Green lab
            ((88, 28, 135), (147, 51, 234)),  # Purple hall
            ((120, 53, 15), (180, 83, 9)),    # Amber seminar
        ]
        all_classrooms_rec = env['university.classroom'].search([])
        for idx, room in enumerate(all_classrooms_rec):
            if not room.image_1920:
                c1, c2 = room_palettes[idx % len(room_palettes)]
                cap = room.capacity or 30
                rtype = room.room_type or "Lecture Room"
                cover_b64 = create_classroom_cover(room.name, rtype, cap, c1, c2)
                room.image_1920 = cover_b64
                print(f"  Generated graphic cover for classroom: {room.name}")
                
        # 6. GENERATE & SEED IMAGES FOR ACADEMIC YEARS
        print("\n--- Seeding Academic Year Badges ---")
        all_academic_years = env['university.academic.year'].search([])
        for ay in all_academic_years:
            if not ay.image_1920:
                img_b64 = create_academic_year_cover(ay.name, ay.current)
                ay.image_1920 = img_b64
                print(f"  Generated badge for academic year: {ay.name}")
                
        cr.commit()
        print("\n>>> ALL WORKLOADS AND IMAGES COMMITTED TO DATABASE! <<<")

if __name__ == "__main__":
    main()
