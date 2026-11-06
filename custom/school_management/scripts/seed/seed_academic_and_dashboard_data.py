import os
import sys
import datetime
import random

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry
from odoo import api, fields, SUPERUSER_ID

def run_seed():
    print("=== STARTING ACADEMIC & DASHBOARD SEED SCRIPT ===")
    odoo.tools.config.parse_config(["-c", "odoo.conf", "-d", "odoo"])
    registry = Registry("odoo")
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # 1. ACADEMIC YEAR & SEMESTER
        academic_year = env['university.academic.year'].search([('current', '=', True)], limit=1)
        if not academic_year:
            academic_year = env['university.academic.year'].search([], order='date_start desc', limit=1)
        print(f"Current Academic Year: {academic_year.name} (id={academic_year.id})")
        
        semester = env['university.semester'].search([
            ('academic_year_id', '=', academic_year.id),
            ('active', '=', True)
        ], limit=1)
        if not semester:
            semester = env['university.semester'].search([], limit=1)
        print(f"Active Semester: {semester.name} (id={semester.id})")
        
        teachers = env['university.teacher'].search([('active', '=', True)])
        students = env['university.student'].search([('status', '=', 'active')])
        sections = env['university.class.section'].search([])
        subjects = env['university.subject'].search([])
        classrooms = env['university.classroom'].search([('status', '=', 'available')])
        if not classrooms:
            classrooms = env['university.classroom'].search([])
        
        print(f"Found {len(teachers)} teachers, {len(students)} active students, {len(sections)} sections, {len(subjects)} subjects, {len(classrooms)} classrooms.")
        
        # ==============================================================
        # 1. TIMESLOTS (Ensure complete Monday-Saturday coverage)
        # ==============================================================
        print("\n--- Seeding / Ensuring Complete Timeslots ---")
        new_ts_count = 0
        days_to_seed = ["0", "1", "2", "3", "4", "5"]
        time_ranges = [
            (8.0, 9.5),
            (9.75, 11.25),
            (13.5, 15.0),
            (15.25, 16.75),
        ]
        
        for d in days_to_seed:
            for sh, eh in time_ranges:
                existing = env['university.timeslot'].search([
                    ('day_of_week', '=', d),
                    ('start_hour', '=', sh),
                    ('end_hour', '=', eh)
                ], limit=1)
                if not existing:
                    ts = env['university.timeslot'].create({
                        'day_of_week': d,
                        'start_hour': sh,
                        'end_hour': eh,
                        'active': True,
                    })
                    new_ts_count += 1
        print(f"Created {new_ts_count} new timeslots. Total timeslots now: {env['university.timeslot'].search_count([])}")
        
        all_timeslots = env['university.timeslot'].search([('active', '=', True)])
        
        # ==============================================================
        # 2. TIMETABLE SLOTS / SCHEDULED SESSIONS
        # ==============================================================
        print("\n--- Seeding Realistic Timetable Sessions ---")
        existing_tt = env['university.timetable.slot'].search_count([])
        print(f"Existing timetable slots: {existing_tt}")
        
        base_monday = datetime.date(2026, 10, 19)
        created_tt_slots = 0
        
        for sec in sections:
            existing_for_sec = env['university.timetable.slot'].search_count([('section_id', '=', sec.id)])
            if existing_for_sec < 4:
                sec_teacher = sec.teacher_id or (teachers[random.randint(0, len(teachers)-1)] if teachers else False)
                sec_subj = sec.subject_id or (subjects[random.randint(0, len(subjects)-1)] if subjects else False)
                sec_room = sec.classroom_id or (classrooms[random.randint(0, len(classrooms)-1)] if classrooms else False)
                
                sample_ts = random.sample(list(all_timeslots), min(3, len(all_timeslots)))
                for ts in sample_ts:
                    day_offset = int(ts.day_of_week)
                    session_date = base_monday + datetime.timedelta(days=day_offset)
                    start_dt = datetime.datetime.combine(session_date, datetime.time(int(ts.start_hour), int((ts.start_hour % 1) * 60)))
                    end_dt = datetime.datetime.combine(session_date, datetime.time(int(ts.end_hour), int((ts.end_hour % 1) * 60)))
                    
                    collision = env['university.timetable.slot'].search([
                        ('state', '!=', 'cancelled'),
                        ('start_time', '<', end_dt),
                        ('end_time', '>', start_dt),
                        '|',
                        ('classroom_id', '=', sec_room.id if sec_room else False),
                        ('teacher_id', '=', sec_teacher.id if sec_teacher else False),
                    ], limit=1)
                    
                    if not collision:
                        try:
                            env['university.timetable.slot'].create({
                                'section_id': sec.id,
                                'subject_id': sec_subj.id if sec_subj else False,
                                'teacher_id': sec_teacher.id if sec_teacher else False,
                                'classroom_id': sec_room.id if sec_room else False,
                                'timeslot_id': ts.id,
                                'start_time': start_dt,
                                'end_time': end_dt,
                                'session_type': 'lecture',
                                'state': 'scheduled',
                                'generation_state': 'published',
                            })
                            created_tt_slots += 1
                        except Exception:
                            pass
        print(f"Created {created_tt_slots} new timetable sessions. Total sessions now: {env['university.timetable.slot'].search_count([])}")

        # ==============================================================
        # 3. LESSON PLANS (university.lesson.plan)
        # ==============================================================
        print("\n--- Seeding Detailed Lesson Plans ---")
        lesson_plan_defs = [
            ("CS101: Divide and Conquer Algorithms & Binary Search", "Divide and conquer recursive decomposition, Master Theorem, binary search logarithmic bounds.", "approved"),
            ("CS201: Structural & Creational Design Patterns in Enterprise Systems", "Factory Method, Singleton thread safety, Decorator streams, and Adapter patterns in modern microservices.", "approved"),
            ("CS301: Relational Schema Normalization (3NF & BCNF)", "Functional dependency inference, Armstrong axioms, lossless join decomposition, and BCNF normalization.", "approved"),
            ("SE202: Sprint Planning, Agile Estimation, and Backlog Refinement", "INVEST user story formulation, Planning Poker Fibonacci sizing, velocity tracking, and Definition of Done.", "approved"),
            ("EE101: AC Circuit Analysis & Phasor Representation", "Phasor transformation of sinusoidal steady states, complex impedance in RLC networks, and Kirchhoff AC laws.", "approved"),
            ("EE203: Microcontroller GPIO, Interrupts, and Hardware Timers", "ARM Cortex-M NVIC configuration, interrupt latency, debouncing, and PWM motor speed regulation.", "approved"),
            ("BA101: Strategic Porter's Five Forces & VRIO Framework", "Industry structural attractiveness analysis, threat of substitutes, and sustainable competitive moat evaluation.", "approved"),
            ("BA202: Corporate Financial Statement Analysis & Ratio Modeling", "DuPont three-step ROE deconstruction, working capital cycle, liquidity ratios, and cash flow quality analysis.", "approved"),
            ("MK101: Omnichannel Customer Journey Mapping & Conversion Optimization", "Multi-touch attribution modeling, CAC to LTV unit economics, retention curves, and A/B funnel testing.", "approved"),
            ("NS101: Sterile Technique, Infection Control & Wound Dressing Protocols", "Surgical asepsis, ultraviolet hand hygiene audits, wound irrigation, sterile field integrity, and staging.", "approved"),
            ("NS204: Intravenous Medication Administration & Critical Dosage Calculations", "Dimensional analysis, IV drip flow rate (mL/hr) calculations, secondary piggyback infusions, and allergy checks.", "approved"),
            ("AI401: Convolutional Neural Networks & Computer Vision Architectures", "2D convolution operations, pooling kernels, ResNet skip connections, and transfer learning fine-tuning.", "approved"),
            ("CY301: Network Packet Inspection & Penetration Defense", "Wireshark packet dissection, TCP handshake flags, SYN flood mitigation, and custom Snort IDS rules.", "approved"),
            ("DS201: Exploratory Data Analysis & Feature Engineering", "Multivariate outlier detection, missing data imputation strategies, Box-Cox transformations, and correlation matrices.", "approved"),
            ("CS402: Senior Capstone Software Architecture & Non-Functional Requirements", "High-level component diagrams, SLA latency budgets, fault tolerance, and API contract specifications.", "draft"),
        ]
        
        created_lp_count = 0
        for idx, (title, desc, st_val) in enumerate(lesson_plan_defs):
            existing = env['university.lesson.plan'].search([('name', '=', title)], limit=1)
            if not existing:
                sec = sections[idx % len(sections)] if sections else False
                subj = sec.subject_id if sec and sec.subject_id else (subjects[idx % len(subjects)] if subjects else False)
                teacher = sec.teacher_id if sec and sec.teacher_id else (teachers[idx % len(teachers)] if teachers else False)
                
                full_description = f"""
                <div class=\"lesson-plan-content\">
                    <p class=\"lead\"><strong>Overview:</strong> {desc}</p>
                    <hr/>
                    <h4>1. Learning Objectives</h4>
                    <ul>
                        <li>Master theoretical principles and core mathematical/algorithmic formulations.</li>
                        <li>Apply industry-standard tools and methodologies to solve practical domain problems.</li>
                        <li>Demonstrate analytical rigor and complete assessment deliverables within deadlines.</li>
                    </ul>
                    <h4>2. Required Materials &amp; Pre-Reading</h4>
                    <p>Standard textbook chapters, university online repository readings, and lab workstation software environments.</p>
                    <h4>3. In-Class Pedagogical Activities</h4>
                    <ol>
                        <li>Theoretical lecture and conceptual interactive review (25 mins).</li>
                        <li>Hands-on laboratory / collaborative case study exercise (45 mins).</li>
                        <li>Plenary group discussion, Q&amp;A, and deliverable debriefing (20 mins).</li>
                    </ol>
                    <h4>4. Assessment &amp; Evaluation</h4>
                    <p>Formative in-class quiz, structured problem set submission, and peer-reviewed code/report evaluation.</p>
                </div>
                """
                env['university.lesson.plan'].create({
                    'name': title,
                    'teacher_id': teacher.id if teacher else False,
                    'subject_id': subj.id if subj else False,
                    'section_id': sec.id if sec else False,
                    'description': full_description,
                    'share_to': 'all',
                    'state': st_val,
                })
                created_lp_count += 1
        print(f"Created {created_lp_count} rich lesson plans. Total lesson plans now: {env['university.lesson.plan'].search_count([])}")

        # ==============================================================
        # 4. SERVICE HOURS (university.service.hour)
        # ==============================================================
        print("\n--- Seeding Realistic Student Service Hours ---")
        service_data = [
            ("Peer Tutoring in Data Structures & Algorithms", 12.0, "approved", "Conducted bi-weekly peer problem solving and code review sessions for struggling first-year engineering students."),
            ("Campus Sustainability & Green Energy Audit", 15.0, "approved", "Collaborated with University Facilities management to audit building energy consumption and solar efficiency."),
            ("Community Health Clinic Volunteer Assistant", 18.0, "approved", "Assisted triage registered nurses with vital sign recording, patient queue management, and pediatric check-ins."),
            ("STEM Robotics Workshop for High School Students", 10.0, "approved", "Led hands-on Arduino and line-following robotics workshops for 40 local high school students during science week."),
            ("University Library Digital Archiving Project", 14.0, "approved", "Scanned, cataloged, and indexed historical university research papers into the digital institutional repository."),
            ("Student IT Helpdesk & Hardware Repair Volunteer", 20.0, "approved", "Provided free laptop diagnosis, malware removal, and RAM/SSD upgrade assistance for undergraduate students."),
            ("First-Year Student Orientation Mentor", 8.0, "approved", "Guided groups of 15 incoming freshmen through campus facilities, course registration, and lab safety rules."),
            ("Annual Red Cross Blood Donation Drive Coordinator", 12.0, "approved", "Managed donor registration, refreshment station, and medical questionnaire intake for 180 donors."),
            ("Public Hospital Blood Pressure Screening Day", 16.0, "approved", "Performed automated and manual blood pressure readings for over 120 elderly visitors during World Health Day."),
            ("Free Python Programming Weekend Bootcamp", 16.0, "approved", "Co-taught intro to programming fundamentals and algorithmic thinking for underprivileged youth."),
            ("Campus Rooftop Solar Panel Maintenance & Data Logging", 10.0, "approved", "Assisted faculty researchers in cleaning photovoltaic arrays and logging daily irradiance vs power output curves."),
            ("Elderly Center Digital Literacy & Smartphone Classes", 8.0, "approved", "Instructed 15 senior citizens on using telemedicine apps, digital messaging, and avoiding internet scams."),
            ("Pediatric Ward Storytelling and Play Therapy Volunteer", 12.0, "approved", "Engaged hospitalized pediatric patients in educational games, reading, and creative arts to alleviate anxiety."),
            ("Robotics Club Competition Arena Construction", 14.0, "approved", "Fabricated competition playing fields, wired timing gates, and calibrated optical sensors for annual university match."),
            ("Youth Coding Club Mentorship (Scratch & Game Dev)", 6.0, "pending", "Mentored middle school students in designing educational 2D games using Scratch and basic logic."),
            ("University Community Garden Organic Composting Drive", 6.0, "pending", "Organized organic food waste collection from campus cafeterias to produce fertile compost for research gardens."),
            ("National Mathematics Olympiad Invigilation Support", 8.0, "pending", "Assisted faculty with testing hall setup, exam packet security, and timing administration for 300 candidates."),
            ("Peer Tutoring in Organic Chemistry & Biochemistry", 10.0, "pending", "Assisted sophomore nursing and pre-med students with biochemical pathways and metabolic cycle memorization."),
            ("Incomplete Documentation Service Claim", 4.0, "rejected", "Claimed service hours without supervisor sign-off signature or verified host institution timestamp log.")
        ]
        
        created_sh_count = 0
        for i, (name, hours, state_val, desc) in enumerate(service_data):
            existing = env['university.service.hour'].search([('name', '=', name)], limit=1)
            if not existing and len(students) > 0 and len(teachers) > 0:
                std = students[i % len(students)]
                teach = teachers[i % len(teachers)]
                service_date = fields.Date.today() - datetime.timedelta(days=random.randint(3, 40))
                start_dt = datetime.datetime.combine(service_date, datetime.time(9, 0))
                end_dt = start_dt + datetime.timedelta(hours=hours)
                approver_user_id = teach.user_id.id if (state_val == 'approved' and teach.user_id) else (1 if state_val == 'approved' else False)
                
                env['university.service.hour'].create({
                    'name': name,
                    'student_id': std.id,
                    'teacher_id': teach.id,
                    'date': service_date,
                    'start_time': start_dt,
                    'end_time': end_dt,
                    'academic_year_id': academic_year.id,
                    'semester_id': semester.id,
                    'hours': hours,
                    'description': desc,
                    'state': state_val,
                    'approved_by': approver_user_id,
                    'approved_date': service_date if state_val == 'approved' else False,
                })
                created_sh_count += 1
        print(f"Created {created_sh_count} student service hour records. Total service hours now: {env['university.service.hour'].search_count([])}")

        # ==============================================================
        # 5. ASSIGNMENTS & SUBMISSIONS (Grade Assignments)
        # ==============================================================
        print("\n--- Seeding Grade Assignments & Student Submissions ---")
        assign_defs = [
            ("CS101 Problem Set 1: Recursion & Sorting", 100.0, 7),
            ("CS201 Project 1: MVC Architecture & Enterprise Patterns", 100.0, 10),
            ("CS301 Lab 3: Relational Query Optimization", 100.0, 14),
            ("SE202 Sprint 1: Agile Backlog Grooming & User Stories", 100.0, 5),
            ("EE101 Assignment 2: Transient Analysis of RLC Circuits", 100.0, 8),
            ("EE203 Lab Report: Embedded Interrupts and PWM Motor Control", 100.0, 12),
            ("BA101 Case Analysis: Disruptive EV Supply Chains", 100.0, 9),
            ("BA202 Financial Modeling: Multi-Year Cash Flow Projections", 100.0, 11),
            ("MK101 Digital Marketing Strategy & CAC/LTV Attribution", 100.0, 6),
            ("NS101 Clinical Simulation Reflection: Aseptic Wound Care", 100.0, 4),
            ("NS204 Dosage Calculation Exam: Critical Care IV Drips", 100.0, 3),
            ("AI401 Computer Vision: Fine-Tuning ResNet for Medical Imaging", 100.0, 15),
            ("CY301 Penetration Defense: Wireshark Packet Forensics", 100.0, 7),
            ("DS201 Exploratory Data Analysis & Outlier Imputation", 100.0, 10),
            ("CS402 Capstone Phase 1: High-Level System Architecture", 100.0, 20),
        ]
        
        created_assigns = 0
        created_subs = 0
        for i, (title, max_sc, days_due) in enumerate(assign_defs):
            assign = env['university.assignment'].search([('name', '=', title)], limit=1)
            sec = sections[i % len(sections)] if sections else False
            subj = sec.subject_id if sec and sec.subject_id else (subjects[i % len(subjects)] if subjects else False)
            teach = sec.teacher_id if sec and sec.teacher_id else (teachers[i % len(teachers)] if teachers else False)
            
            if not assign and sec:
                assign = env['university.assignment'].create({
                    'name': title,
                    'assignment_type': 'class',
                    'section_id': sec.id,
                    'subject_id': subj.id if subj else False,
                    'teacher_id': teach.id if teach else False,
                    'max_score': max_sc,
                    'due_date': fields.Date.today() + datetime.timedelta(days=days_due),
                    'description': f"<p>Complete all assigned problems and technical requirements for <strong>{title}</strong>. Ensure your work adheres to university academic honesty standards and include relevant code, formulas, and analysis documentation.</p>",
                    'state': 'approved',
                })
                created_assigns += 1
            
            if assign and sec:
                # Find or ensure enrolled students for this section
                enr_recs = env['university.enrollment'].search([
                    ('section_id', '=', sec.id),
                    ('status', '=', 'enrolled')
                ])
                if not enr_recs and students:
                    # Enroll students in section
                    for st in students[i:i+3]:
                        chk = env['university.enrollment'].search([
                            ('student_id', '=', st.id),
                            ('section_id', '=', sec.id)
                        ], limit=1)
                        if not chk:
                            chk = env['university.enrollment'].create({
                                'student_id': st.id,
                                'section_id': sec.id,
                                'subject_id': subj.id if subj else False,
                                'academic_year_id': academic_year.id,
                                'semester_id': semester.id,
                                'status': 'enrolled',
                                'enrollment_date': fields.Date.today() - datetime.timedelta(days=20),
                            })
                    enr_recs = env['university.enrollment'].search([
                        ('section_id', '=', sec.id),
                        ('status', '=', 'enrolled')
                    ])
                
                target_students = enr_recs.mapped('student_id')
                for st in target_students[:3]:
                    sub_exists = env['university.assignment.submission'].search([
                        ('assignment_id', '=', assign.id),
                        ('student_id', '=', st.id)
                    ], limit=1)
                    if not sub_exists:
                        score_val = round(random.uniform(82.0, 97.5), 1)
                        env['university.assignment.submission'].create({
                            'assignment_id': assign.id,
                            'student_id': st.id,
                            'section_id': sec.id,
                            'subject_id': subj.id if subj else False,
                            'teacher_id': teach.id if teach else False,
                            'academic_year_id': academic_year.id,
                            'semester_id': semester.id,
                            'submitted_on': fields.Datetime.now() - datetime.timedelta(days=random.randint(1, 5)),
                            'answer_text': f"Completed assignment '{title}'. Attached solution source code and comprehensive test results demonstrating full specification compliance.",
                            'score': score_val,
                            'max_score': max_sc,
                            'state': 'approved',
                            'feedback': f"Excellent work on this submission! Thorough analysis, well-structured logic, and clean presentation. Awarded {score_val} / {max_sc}.",
                        })
                        created_subs += 1
                        
        print(f"Created {created_assigns} class assignments and {created_subs} evaluated submissions. Total assignments: {env['university.assignment'].search_count([])}, Total submissions: {env['university.assignment.submission'].search_count([])}")

        # ==============================================================
        # 6. AT-RISK STUDENTS & ADVISING FOLLOWUPS (Fix Dashboard Real Data)
        # ==============================================================
        print("\n--- Updating Student Risk Levels & Advising Followups ---")
        curr_active_students = env['university.student'].search([
            ('academic_year_id', '=', academic_year.id),
            ('status', '=', 'active')
        ], order='id asc')
        if len(curr_active_students) >= 12:
            high_risk_reasons = [
                "Attendance dropped to 64%, missed 2 mandatory midterms; academic probation warning.",
                "Cumulative GPA 1.94, failing CS201 and EE101 prerequisites.",
                "Repeated absences across 3 core subjects; unresolved fee balance and family emergency.",
                "Low attendance (68%) and unsubmitted laboratory assignments in Software Engineering.",
            ]
            for idx, reason in enumerate(high_risk_reasons):
                st = curr_active_students[idx]
                st.write({
                    'risk_level': 'high',
                    'risk_reason': reason,
                    'gpa': round(random.uniform(1.85, 2.15), 2),
                    'attendance_rate': round(random.uniform(62.0, 71.0), 1),
                })
                existing_fup = env['university.student.followup'].search([('student_id', '=', st.id)], limit=1)
                if not existing_fup:
                    env['university.student.followup'].create({
                        'title': f"Urgent Academic Intervention: {st.name}",
                        'student_id': st.id,
                        'advisor_id': st.advisor_id.id if st.advisor_id else (teachers[0].id if teachers else False),
                        'action_type': 'meeting',
                        'date_deadline': fields.Date.today() + datetime.timedelta(days=random.randint(2, 7)),
                        'state': 'pending',
                        'description': f"Mandatory in-person advising meeting to establish Academic Performance Improvement Contract. Reason: {reason}",
                        'visible_to_student': True,
                    })
            
            medium_risk_reasons = [
                ("GPA marginal at 2.38; requires tutoring assistance in algorithms and database design.", "tutoring"),
                ("Missed 4 class sessions during exam week; under review for attendance threshold.", "attendance_check"),
                ("Prerequisite deficiency in Calculus II; recommended for peer study groups.", "tutoring"),
                ("Dropped from Honors track due to semester GPA slip to 2.45.", "meeting"),
                ("Midterm scores below class average in Circuit Analysis; advising check-in requested.", "tutoring"),
                ("Borderline academic progress; advisor check scheduled before course withdrawal deadline.", "meeting"),
                ("Requires time management counseling and study schedule restructuring.", "tutoring"),
                ("Recovering from illness; working with faculty on makeup assignment plan.", "assignment_catchup"),
            ]
            for idx, (reason, act_type) in enumerate(medium_risk_reasons):
                st = curr_active_students[4 + idx]
                st.write({
                    'risk_level': 'medium',
                    'risk_reason': reason,
                    'gpa': round(random.uniform(2.32, 2.58), 2),
                    'attendance_rate': round(random.uniform(75.0, 83.0), 1),
                })
                existing_fup = env['university.student.followup'].search([('student_id', '=', st.id)], limit=1)
                if not existing_fup:
                    env['university.student.followup'].create({
                        'title': f"Academic Progress Check-in: {st.name}",
                        'student_id': st.id,
                        'advisor_id': st.advisor_id.id if st.advisor_id else (teachers[0].id if teachers else False),
                        'action_type': act_type,
                        'date_deadline': fields.Date.today() + datetime.timedelta(days=random.randint(4, 12)),
                        'state': 'in_progress',
                        'description': f"Check-in on student progress and referral to tutoring lab. Reason: {reason}",
                        'visible_to_student': True,
                    })
                    
            print(f"Successfully updated 4 high-risk and 8 medium-risk students in academic year {academic_year.name}.")

        cr.commit()
        print("=== COMMITTED ALL ACADEMIC & DASHBOARD DATA SEEDS TO DATABASE ===")

if __name__ == '__main__':
    run_seed()
