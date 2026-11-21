import sys
import os
import random

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

def run():
    odoo.tools.config.parse_config(['-c', 'odoo.conf', '-d', 'odoo'])
    registry = Registry('odoo')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        print("=== ENRICHING SUBJECT ECOSYSTEM: TEACHERS, SECTIONS & SYLLABI ===")

        # 1. Fetch Key Reference Records
        dept_cs = env['university.department'].search([('code', '=', 'CS')], limit=1)
        dept_se = env['university.department'].search([('code', '=', 'SE')], limit=1)
        dept_ai = env['university.department'].search([('code', '=', 'AI')], limit=1)
        dept_ee = env['university.department'].search([('code', '=', 'EE')], limit=1)
        dept_med = env['university.department'].search([('code', '=', 'MED')], limit=1)
        dept_nur = env['university.department'].search([('code', '=', 'NUR')], limit=1)
        dept_mgt = env['university.department'].search([('code', '=', 'MGT')], limit=1)
        dept_mkt = env['university.department'].search([('code', '=', 'MKT')], limit=1)
        dept_fin = env['university.department'].search([('code', '=', 'FIN')], limit=1)

        sem1 = env['university.semester'].search([('semester_type', '=', 'semester_1'), ('academic_year_id.name', 'ilike', '2026')], limit=1)
        if not sem1:
            sem1 = env['university.semester'].search([('active', '=', True)], limit=1)

        classrooms = env['university.classroom'].search([('active', '=', True)])
        labs = classrooms.filtered(lambda c: c.room_type == 'lab') or classrooms
        lecture_halls = classrooms.filtered(lambda c: c.room_type in ('lecture_hall', 'auditorium')) or classrooms
        std_rooms = classrooms.filtered(lambda c: c.room_type == 'classroom') or classrooms

        print(f"Active Semester: {sem1.name} (ID: {sem1.id})")
        print(f"Total Classrooms Available: {len(classrooms)}")

        # 2. Ensure Distinguished Faculty in Departments
        teacher_definitions = [
            # Finance & Accounting
            {
                "name": "Prof. Benjamin Graham",
                "teacher_id": "T-FIN01",
                "department_id": dept_fin.id,
                "email": "benjamin.graham@faculty.university.edu",
                "phone": "+855 23 881 101",
                "specialization": "Value Investing, Security Analysis & Financial Statement Auditing",
                "qualification": "PhD in Financial Economics, Columbia University",
            },
            {
                "name": "Dr. Eugene Fama",
                "teacher_id": "T-FIN02",
                "department_id": dept_fin.id,
                "email": "eugene.fama@faculty.university.edu",
                "phone": "+855 23 881 102",
                "specialization": "Empirical Asset Pricing, Market Efficiency & Financial Econometrics",
                "qualification": "PhD in Economics & Finance, University of Chicago",
            },
            {
                "name": "Prof. Merton Miller",
                "teacher_id": "T-FIN03",
                "department_id": dept_fin.id,
                "email": "merton.miller@faculty.university.edu",
                "phone": "+855 23 881 103",
                "specialization": "Corporate Finance, Capital Structure, Valuation & Dividend Policy",
                "qualification": "PhD in Economics, Johns Hopkins University",
            },
            {
                "name": "Dr. Myron Scholes",
                "teacher_id": "T-FIN04",
                "department_id": dept_fin.id,
                "email": "myron.scholes@faculty.university.edu",
                "phone": "+855 23 881 104",
                "specialization": "Financial Engineering, Derivatives Pricing & Market Risk Hedging",
                "qualification": "PhD in Financial Economics, Stanford University",
            },
            # Nursing & Public Health
            {
                "name": "Dr. Mary Seacole",
                "teacher_id": "T-NUR03",
                "department_id": dept_nur.id,
                "email": "mary.seacole@faculty.university.edu",
                "phone": "+855 23 881 201",
                "specialization": "Clinical Nursing Practice, Emergency Trauma Care & Hospital Asepsis",
                "qualification": "Doctor of Nursing Practice (DNP), King's College London",
            },
            {
                "name": "Dr. Paul Farmer",
                "teacher_id": "T-NUR04",
                "department_id": dept_nur.id,
                "email": "paul.farmer@faculty.university.edu",
                "phone": "+855 23 881 202",
                "specialization": "Global Health Equity, Infectious Disease Epidemiology & Community Medicine",
                "qualification": "MD, PhD in Medical Anthropology, University of Cambridge",
            },
            {
                "name": "Prof. Patricia Benner",
                "teacher_id": "T-NUR05",
                "department_id": dept_nur.id,
                "email": "patricia.benner@faculty.university.edu",
                "phone": "+855 23 881 203",
                "specialization": "Advanced Clinical Nursing Pedagogy, Critical Care & Patient Safety",
                "qualification": "PhD in Nursing Science, UC Berkeley",
            },
            {
                "name": "Dr. William Osler",
                "teacher_id": "T-NUR06",
                "department_id": dept_nur.id,
                "email": "william.osler@faculty.university.edu",
                "phone": "+855 23 881 204",
                "specialization": "Clinical Pathophysiology, Bedside Diagnostic Examination & Medical Ethics",
                "qualification": "MD, FRCP, McGill University",
            },
            # Software Engineering
            {
                "name": "Prof. Martin Fowler",
                "teacher_id": "T-SE03",
                "department_id": dept_se.id,
                "email": "martin.fowler@faculty.university.edu",
                "phone": "+855 23 881 301",
                "specialization": "Enterprise Application Architecture, Code Refactoring & Microservices",
                "qualification": "MSc in Computer Science, University College London",
            },
            {
                "name": "Dr. Linus Torvalds",
                "teacher_id": "T-SE04",
                "department_id": dept_se.id,
                "email": "linus.torvalds@faculty.university.edu",
                "phone": "+855 23 881 302",
                "specialization": "Operating System Kernels, Distributed Git Systems & Systems Engineering",
                "qualification": "Hon. PhD in Computer Science, University of Helsinki",
            },
            {
                "name": "Prof. Fred Brooks",
                "teacher_id": "T-SE05",
                "department_id": dept_se.id,
                "email": "fred.brooks@faculty.university.edu",
                "phone": "+855 23 881 303",
                "specialization": "Software Engineering Management, System Architecture & Agile Methodologies",
                "qualification": "PhD in Applied Mathematics, MIT",
            },
            # Artificial Intelligence & Data Science
            {
                "name": "Prof. Andrew Ng",
                "teacher_id": "T-AI04",
                "department_id": dept_ai.id,
                "email": "andrew.ng@faculty.university.edu",
                "phone": "+855 23 881 401",
                "specialization": "Machine Learning, Deep Neural Networks & Large-Scale AI Deployment",
                "qualification": "PhD in Computer Science, UC Berkeley",
            },
            {
                "name": "Dr. Demis Hassabis",
                "teacher_id": "T-AI05",
                "department_id": dept_ai.id,
                "email": "demis.hassabis@faculty.university.edu",
                "phone": "+855 23 881 402",
                "specialization": "Deep Reinforcement Learning, Computational Neuroscience & AI Ethics",
                "qualification": "PhD in Cognitive Neuroscience, University College London",
            },
            # Management & Strategy
            {
                "name": "Prof. Clayton Christensen",
                "teacher_id": "T-MGT04",
                "department_id": dept_mgt.id,
                "email": "clayton.c@faculty.university.edu",
                "phone": "+855 23 881 501",
                "specialization": "Disruptive Innovation, Strategic Business Models & Corporate Evolution",
                "qualification": "DBA, Stanford Graduate School of Business",
            },
            {
                "name": "Dr. Henry Mintzberg",
                "teacher_id": "T-MGT05",
                "department_id": dept_mgt.id,
                "email": "henry.mintzberg@faculty.university.edu",
                "phone": "+855 23 881 502",
                "specialization": "Managerial Strategy, Organizational Structures & Strategic Decision Dynamics",
                "qualification": "PhD in Management, MIT Sloan School of Management",
            },
            # Marketing & Logistics
            {
                "name": "Prof. David Aaker",
                "teacher_id": "T-MKT03",
                "department_id": dept_mkt.id,
                "email": "david.aaker@faculty.university.edu",
                "phone": "+855 23 881 601",
                "specialization": "Strategic Brand Leadership, Brand Identity & Global Marketing Architecture",
                "qualification": "PhD in Business Administration, Stanford University",
            },
            {
                "name": "Dr. Martin Christopher",
                "teacher_id": "T-MKT04",
                "department_id": dept_mkt.id,
                "email": "martin.christopher@faculty.university.edu",
                "phone": "+855 23 881 602",
                "specialization": "Logistics Engineering, Global Supply Chain Agility & Customer Value",
                "qualification": "PhD in Marketing & Logistics, Cranfield University",
            },
        ]

        created_teachers = 0
        for tdata in teacher_definitions:
            if not tdata.get("department_id"):
                continue
            existing = env['university.teacher'].search([('teacher_id', '=', tdata['teacher_id'])], limit=1)
            if not existing:
                env['university.teacher'].create(tdata)
                created_teachers += 1
                print(f"  + Added Professor: {tdata['name']} ({tdata['specialization'][:35]}...)")
        print(f"Distinguished faculty created: {created_teachers}")

        # Map department to pool of teachers
        all_teachers = env['university.teacher'].search([])
        dept_teachers_map = {}
        for t in all_teachers:
            if t.department_id:
                dept_teachers_map.setdefault(t.department_id.id, []).append(t)

        # 3. Process All Subjects
        all_subjects = env['university.subject'].search([])
        print(f"\nProcessing {len(all_subjects)} University Subjects...")

        updated_teachers_count = 0
        updated_desc_count = 0
        created_sections_count = 0

        for subj in all_subjects:
            code = subj.code or "SUBJ"
            name = subj.name or "Course"
            dept = subj.department_id
            dept_name = dept.name if dept else "General Academic Studies"

            # A. TEACHER ASSIGNMENT
            if not subj.teacher_ids:
                pool = dept_teachers_map.get(dept.id, []) if dept else []
                if not pool:
                    pool = list(all_teachers)
                if pool:
                    selected_teachers = random.sample(pool, min(len(pool), 2))
                    subj.teacher_ids = [(6, 0, [t.id for t in selected_teachers])]
                    updated_teachers_count += 1

            # B. COURSE DESCRIPTION & SYLLABUS
            if not subj.description or len(subj.description.strip()) < 20:
                clean_desc = (
                    f"{name} ({code}) is a comprehensive {subj.credits}-credit academic course offered by the {dept_name}. "
                    f"This course provides students with fundamental and advanced theoretical frameworks, rigorous methodological tools, "
                    f"and real-world practical problem-solving capabilities required in modern industry and academic research. "
                    f"Through interactive lectures, structured seminars, and applied projects, learners critically evaluate core concepts, "
                    f"design evidence-based solutions, and develop high-level competence in professional practice."
                )

                syllabus_html = f"""
                <div class="course-syllabus-wrapper p-3 border rounded bg-light">
                    <div class="d-flex align-items-center mb-3">
                        <span class="badge text-bg-primary me-2 px-3 py-2 fs-6">{code}</span>
                        <h4 class="mb-0 text-dark font-weight-bold">{name}</h4>
                    </div>
                    <div class="row g-3 mb-4">
                        <div class="col-md-4">
                            <div class="p-2 border rounded bg-white shadow-sm">
                                <small class="text-muted d-block text-uppercase font-weight-bold">Department</small>
                                <span class="font-weight-bold text-dark">{dept_name}</span>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-2 border rounded bg-white shadow-sm">
                                <small class="text-muted d-block text-uppercase font-weight-bold">Academic Credits</small>
                                <span class="font-weight-bold text-primary">{subj.credits} Credit Units</span>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-2 border rounded bg-white shadow-sm">
                                <small class="text-muted d-block text-uppercase font-weight-bold">Delivery Mode</small>
                                <span class="font-weight-bold text-success">Lectures &amp; Applied Practicum</span>
                            </div>
                        </div>
                    </div>

                    <h5 class="text-primary border-bottom pb-2 mb-3"><i class="fa fa-bullseye me-2"></i>Course Learning Objectives</h5>
                    <ul class="mb-4">
                        <li>Master essential theoretical foundations and industry-standard best practices in <strong>{name}</strong>.</li>
                        <li>Formulate analytical and quantitative models to evaluate complex practical problems systematically.</li>
                        <li>Execute applied hands-on laboratory exercises, team case studies, and modern technological workflows.</li>
                        <li>Communicate technical and scientific findings clearly across interdisciplinary professional environments.</li>
                    </ul>

                    <h5 class="text-primary border-bottom pb-2 mb-3"><i class="fa fa-list-ol me-2"></i>Curriculum Modules &amp; Weekly Topics</h5>
                    <table class="table table-sm table-striped table-bordered bg-white mb-4">
                        <thead class="table-primary">
                            <tr>
                                <th style="width: 15%;">Module</th>
                                <th style="width: 50%;">Core Subject Topic</th>
                                <th style="width: 35%;">Practical Deliverable / Case Study</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong>Module 1</strong></td>
                                <td>Foundations, Historical Paradigm &amp; Core Principles of {name}</td>
                                <td>Introductory Diagnostic &amp; Literature Review</td>
                            </tr>
                            <tr>
                                <td><strong>Module 2</strong></td>
                                <td>Architectural Frameworks, Methodologies &amp; Standards</td>
                                <td>Applied Framework Design &amp; Problem Sets</td>
                            </tr>
                            <tr>
                                <td><strong>Module 3</strong></td>
                                <td>Advanced Implementation, Analytical Techniques &amp; Tools</td>
                                <td>Midterm Practical Case Study / Lab Experiment</td>
                            </tr>
                            <tr>
                                <td><strong>Module 4</strong></td>
                                <td>Optimization, Security, Governance &amp; Industry Standards</td>
                                <td>Independent Research Paper &amp; Benchmark Report</td>
                            </tr>
                            <tr>
                                <td><strong>Module 5</strong></td>
                                <td>Comprehensive Capstone Synthesis &amp; Oral Defense</td>
                                <td>Final Project Defense &amp; Comprehensive Examination</td>
                            </tr>
                        </tbody>
                    </table>

                    <h5 class="text-primary border-bottom pb-2 mb-3"><i class="fa fa-check-circle me-2"></i>Grading &amp; Assessment Criteria</h5>
                    <div class="row text-center g-2">
                        <div class="col-3">
                            <div class="p-2 border rounded bg-white"><div class="fw-bold text-dark">Quizzes &amp; Homework</div><div class="text-primary fs-5 fw-bold">20%</div></div>
                        </div>
                        <div class="col-3">
                            <div class="p-2 border rounded bg-white"><div class="fw-bold text-dark">Midterm Exam</div><div class="text-primary fs-5 fw-bold">25%</div></div>
                        </div>
                        <div class="col-3">
                            <div class="p-2 border rounded bg-white"><div class="fw-bold text-dark">Term Project &amp; Labs</div><div class="text-primary fs-5 fw-bold">25%</div></div>
                        </div>
                        <div class="col-3">
                            <div class="p-2 border rounded bg-white"><div class="fw-bold text-dark">Final Examination</div><div class="text-primary fs-5 fw-bold">30%</div></div>
                        </div>
                    </div>
                </div>
                """

                subj.write({
                    'description': clean_desc,
                    'syllabus_html': syllabus_html,
                })
                updated_desc_count += 1

            # C. CLASS SECTION GENERATION
            if not subj.section_ids:
                assigned_teacher = subj.teacher_ids[:1] if subj.teacher_ids else env['university.teacher'].browse(False)
                
                is_lab_subject = any(term in name.lower() for term in ['lab', 'programming', 'network', 'circuit', 'microbiology', 'anatomy', 'chemistry', 'electronics', 'robotics'])
                is_biz_subject = any(term in name.lower() for term in ['management', 'marketing', 'finance', 'business', 'accounting', 'economics', 'strategy'])
                
                if is_lab_subject and labs:
                    chosen_room = random.choice(labs)
                elif is_biz_subject and lecture_halls:
                    chosen_room = random.choice(lecture_halls)
                elif std_rooms:
                    chosen_room = random.choice(std_rooms)
                else:
                    chosen_room = classrooms[:1] if classrooms else False

                sec_name = f"{code}-SEC01"
                existing_sec = env['university.class.section'].search([('name', '=', sec_name)], limit=1)
                if not existing_sec:
                    env['university.class.section'].create({
                        'name': sec_name,
                        'section_type': 'course',
                        'subject_id': subj.id,
                        'teacher_id': assigned_teacher.id if assigned_teacher else False,
                        'semester_id': sem1.id,
                        'classroom_id': chosen_room.id if chosen_room else False,
                        'capacity': 40,
                    })
                    created_sections_count += 1

        # Recompute counts
        all_subjects._compute_counts()
        cr.commit()

        print("\n========================================================")
        print(">>> SUBJECT ECOSYSTEM ENRICHMENT COMPLETED SUCCESSFULLY <<<")
        print(f"Total Subjects Audited: {len(all_subjects)}")
        print(f"Subjects Assigned Instructors: {updated_teachers_count}")
        print(f"Subjects Populated with Syllabus/Description: {updated_desc_count}")
        print(f"New Course Class Sections Created: {created_sections_count}")
        print("========================================================")

if __name__ == '__main__':
    run()
