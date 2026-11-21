-- ==============================================================================
-- University Management System - Complete Database Seed Script (.sql)
-- Generated for Odoo Module: school_management
-- ==============================================================================
-- Instructions:
-- Run this script in PostgreSQL (psql or pgAdmin) while connected to your database:
-- psql -d <your_database_name> -U <username> -f custom/school_management/seed_data.sql
-- ==============================================================================

BEGIN;

-- ------------------------------------------------------------------------------
-- 1. ACADEMIC YEARS
-- ------------------------------------------------------------------------------
INSERT INTO university_academic_year (id, name, date_start, date_end, current, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, '2025-2026 Academic Year', '2025-09-01', '2026-06-30', true, true, 1, NOW(), 1, NOW()),
  (2, '2026-2027 Academic Year', '2026-09-01', '2027-06-30', false, true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 2. SEMESTERS
-- ------------------------------------------------------------------------------
INSERT INTO university_semester (id, name, academic_year_id, semester_type, date_start, date_end, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'Fall 2025 (Semester 1)', 1, 'semester_1', '2025-09-01', '2025-12-20', true, 1, NOW(), 1, NOW()),
  (2, 'Spring 2026 (Semester 2)', 1, 'semester_2', '2026-01-10', '2026-05-15', true, 1, NOW(), 1, NOW()),
  (3, 'Summer 2026', 1, 'summer', '2026-06-01', '2026-08-15', true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 3. CLASSROOMS
-- ------------------------------------------------------------------------------
INSERT INTO university_classroom (id, name, building, floor, capacity, room_type, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'Hall A-101', 'Building A', '1st Floor', 120, 'lecture_hall', true, 1, NOW(), 1, NOW()),
  (2, 'Lab B-205', 'Building B', '2nd Floor', 35, 'lab', true, 1, NOW(), 1, NOW()),
  (3, 'Seminar C-302', 'Building C', '3rd Floor', 40, 'seminar_room', true, 1, NOW(), 1, NOW()),
  (4, 'Classroom A-102', 'Building A', '1st Floor', 50, 'classroom', true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 4. FACULTIES
-- ------------------------------------------------------------------------------
INSERT INTO university_faculty (id, name, code, description, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'Faculty of Engineering & Technology', 'ENG', 'Engineering, Computer Science, and Robotics', true, 1, NOW(), 1, NOW()),
  (2, 'Faculty of Business & Administration', 'BUS', 'Business Administration, Finance, and Accounting', true, 1, NOW(), 1, NOW()),
  (3, 'Faculty of Science & Medicine', 'SCI', 'Biological Sciences, Chemistry, and Public Health', true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 5. DEPARTMENTS
-- ------------------------------------------------------------------------------
INSERT INTO university_department (id, name, code, faculty_id, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'Department of Computer Science', 'CS', 1, true, 1, NOW(), 1, NOW()),
  (2, 'Department of Electrical Engineering', 'EE', 1, true, 1, NOW(), 1, NOW()),
  (3, 'Department of Business Management', 'BM', 2, true, 1, NOW(), 1, NOW()),
  (4, 'Department of Finance & Banking', 'FB', 2, true, 1, NOW(), 1, NOW()),
  (5, 'Department of Biology & Biotechnology', 'BIO', 3, true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 6. PROGRAMS / MAJORS
-- ------------------------------------------------------------------------------
INSERT INTO university_program (id, name, code, department_id, degree_type, duration_years, total_credits, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'Bachelor of Science in Computer Science', 'BS-CS', 1, 'bachelor', 4, 130, true, 1, NOW(), 1, NOW()),
  (2, 'Bachelor of Engineering in Electrical Engineering', 'BE-EE', 2, 'bachelor', 4, 140, true, 1, NOW(), 1, NOW()),
  (3, 'Bachelor of Business Administration', 'BBA', 3, 'bachelor', 4, 120, true, 1, NOW(), 1, NOW()),
  (4, 'Master of Science in Software Engineering', 'MS-SE', 1, 'master', 2, 60, true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 7. TEACHERS / ACADEMIC STAFF
-- ------------------------------------------------------------------------------
INSERT INTO university_teacher (id, name, teacher_id, gender, date_of_birth, phone, email, address, faculty_id, department_id, position, specialization, qualification, hire_date, is_dean, is_hod, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'Dr. Robert Vance', 'TCH-0001', 'male', '1975-04-12', '+1 555-0101', 'r.vance@university.edu', '123 Academic Way', 1, 1, 'professor', 'Artificial Intelligence & Systems', 'Ph.D. Computer Science', '2012-08-15', true, false, true, 1, NOW(), 1, NOW()),
  (2, 'Dr. Sarah Connor', 'TCH-0002', 'female', '1982-09-24', '+1 555-0102', 's.connor@university.edu', '456 Tech Park', 1, 1, 'associate_professor', 'Software Engineering & Databases', 'Ph.D. Software Engineering', '2016-01-10', false, true, true, 1, NOW(), 1, NOW()),
  (3, 'Prof. Michael Scott', 'TCH-0003', 'male', '1978-03-15', '+1 555-0103', 'm.scott@university.edu', '789 Business Blvd', 2, 3, 'professor', 'Strategic Management & Leadership', 'Ph.D. Business Admin', '2010-09-01', false, true, true, 1, NOW(), 1, NOW()),
  (4, 'Dr. Alice Hamilton', 'TCH-0004', 'female', '1988-11-05', '+1 555-0104', 'a.hamilton@university.edu', '101 Science Ave', 3, 5, 'assistant_professor', 'Molecular Genetics', 'Ph.D. Biology', '2019-08-20', false, false, true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 8. SUBJECTS
-- ------------------------------------------------------------------------------
INSERT INTO university_subject (id, name, code, department_id, credits, description, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'Introduction to Computer Science', 'CS101', 1, 3, 'Foundations of programming and computer architecture.', true, 1, NOW(), 1, NOW()),
  (2, 'Data Structures & Algorithms', 'CS201', 1, 4, 'Arrays, Linked Lists, Trees, Graphs, and Complexity Analysis.', true, 1, NOW(), 1, NOW()),
  (3, 'Database Management Systems', 'CS301', 1, 3, 'Relational model, SQL, Transactions, and Indexing.', true, 1, NOW(), 1, NOW()),
  (4, 'Circuit Analysis & Electronics', 'EE101', 2, 4, 'Basic electrical components, Ohm law, and AC/DC circuits.', true, 1, NOW(), 1, NOW()),
  (5, 'Principles of Management', 'BM101', 3, 3, 'Core concepts of organizational leadership and strategy.', true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- Subject <-> Program Relationship Junction
INSERT INTO university_program_subject_rel (program_id, subject_id)
VALUES 
  (1, 1), (1, 2), (1, 3),
  (2, 4),
  (3, 5)
ON CONFLICT DO NOTHING;

-- Subject <-> Teacher Relationship Junction
INSERT INTO university_teacher_subject_rel (teacher_id, subject_id)
VALUES 
  (1, 1), (1, 2),
  (2, 3),
  (3, 5)
ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------------------------
-- 9. ACADEMIC ROLE ASSIGNMENTS
-- ------------------------------------------------------------------------------
INSERT INTO university_academic_assignment (id, name, staff_id, role, faculty_id, department_id, start_date, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'Dr. Robert Vance - Head of Faculty (Engineering)', 1, 'dean', 1, NULL, '2024-09-01', true, 1, NOW(), 1, NOW()),
  (2, 'Dr. Sarah Connor - Head of Department (CS)', 2, 'department_head', NULL, 1, '2024-09-01', true, 1, NOW(), 1, NOW()),
  (3, 'Prof. Michael Scott - Head of Department (Business)', 3, 'department_head', NULL, 3, '2024-09-01', true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 10. CLASS SECTIONS
-- ------------------------------------------------------------------------------
INSERT INTO university_class_section (id, name, subject_id, teacher_id, semester_id, classroom_id, capacity, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'CS101 - Section A', 1, 1, 1, 1, 40, true, 1, NOW(), 1, NOW()),
  (2, 'CS201 - Section A', 2, 1, 1, 2, 30, true, 1, NOW(), 1, NOW()),
  (3, 'CS301 - Section A', 3, 2, 1, 2, 35, true, 1, NOW(), 1, NOW()),
  (4, 'BM101 - Section A', 5, 3, 1, 3, 45, true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 11. STUDENTS
-- ------------------------------------------------------------------------------
INSERT INTO university_student (id, name, student_id, gender, date_of_birth, email, phone, address, emergency_contact_name, emergency_contact_phone, faculty_id, department_id, program_id, academic_year_id, current_semester_id, status, active, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'John Doe', 'STU-2025-001', 'male', '2004-05-14', 'john.doe@student.university.edu', '+1 555-0201', '12 College St', 'Mary Doe', '+1 555-0901', 1, 1, 1, 1, 1, 'active', true, 1, NOW(), 1, NOW()),
  (2, 'Jane Smith', 'STU-2025-002', 'female', '2005-01-22', 'jane.smith@student.university.edu', '+1 555-0202', '34 Campus Drive', 'Robert Smith', '+1 555-0902', 1, 1, 1, 1, 1, 'active', true, 1, NOW(), 1, NOW()),
  (3, 'Alex Johnson', 'STU-2025-003', 'other', '2003-11-30', 'alex.j@student.university.edu', '+1 555-0203', '56 University Ave', 'Taylor Johnson', '+1 555-0903', 2, 3, 3, 1, 1, 'active', true, 1, NOW(), 1, NOW()),
  (4, 'Emily Brown', 'STU-2025-004', 'female', '2004-08-09', 'emily.b@student.university.edu', '+1 555-0204', '78 Dorms Way', 'David Brown', '+1 555-0904', 1, 1, 1, 1, 1, 'active', true, 1, NOW(), 1, NOW()),
  (5, 'Michael Lee', 'STU-2025-005', 'male', '2004-12-01', 'michael.lee@student.university.edu', '+1 555-0205', '90 Oak Rd', 'Susan Lee', '+1 555-0905', 1, 1, 1, 1, 1, 'active', true, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 8. STUDENT AUTHENTICATION (student <-> res.users unique link)
-- ------------------------------------------------------------------------------
-- Note: Student portal accounts (res.users) are intentionally NOT seeded here.
-- They are created through the portal signup flow (see models/res_users.py),
-- which guarantees a one-to-one link between a student record and its login.
-- 

-- ------------------------------------------------------------------------------
-- 12. ENROLLMENTS
-- ------------------------------------------------------------------------------
INSERT INTO university_enrollment (id, student_id, program_id, section_id, subject_id, teacher_id, academic_year_id, semester_id, faculty_id, enrollment_date, status, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 1, 1, 1, 1, 1, 1, 1, 1, '2025-09-02', 'enrolled', 1, NOW(), 1, NOW()),
  (2, 1, 1, 3, 3, 2, 1, 1, 1, '2025-09-02', 'enrolled', 1, NOW(), 1, NOW()),
  (3, 2, 1, 1, 1, 1, 1, 1, 1, '2025-09-03', 'enrolled', 1, NOW(), 1, NOW()),
  (4, 3, 3, 4, 5, 3, 1, 1, 2, '2025-09-04', 'enrolled', 1, NOW(), 1, NOW()),
  (5, 4, 1, 1, 1, 1, 1, 1, 1, '2025-09-05', 'enrolled', 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 13. FEE INVOICES & LINES
-- ------------------------------------------------------------------------------
INSERT INTO university_fee (id, name, student_id, academic_year_id, semester_id, date, due_date, total_amount, paid_amount, balance, state, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'INV-0001', 1, 1, 1, '2025-09-05', '2025-09-30', 1200.00, 1200.00, 0.00, 'paid', 1, NOW(), 1, NOW()),
  (2, 'INV-0002', 2, 1, 1, '2025-09-05', '2025-09-30', 1200.00, 600.00, 600.00, 'posted', 1, NOW(), 1, NOW()),
  (3, 'INV-0003', 3, 1, 1, '2025-09-06', '2025-09-30', 1000.00, 0.00, 1000.00, 'posted', 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO university_fee_line (id, fee_id, name, amount, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 1, 'Tuition Fee - Fall 2025', 1000.00, 1, NOW(), 1, NOW()),
  (2, 1, 'Computer Lab Access Fee', 200.00, 1, NOW(), 1, NOW()),
  (3, 2, 'Tuition Fee - Fall 2025', 1000.00, 1, NOW(), 1, NOW()),
  (4, 2, 'Library & Activity Fee', 200.00, 1, NOW(), 1, NOW()),
  (5, 3, 'Tuition Fee - Business Admin', 1000.00, 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 14. PAYMENTS
-- ------------------------------------------------------------------------------
INSERT INTO university_payment (id, name, student_id, fee_id, date, amount, payment_method, reference, state, create_uid, create_date, write_uid, write_date)
VALUES 
  (1, 'PAY-0001', 1, 1, '2025-09-10', 1200.00, 'bank_transfer', 'TRX-987654', 'posted', 1, NOW(), 1, NOW()),
  (2, 'PAY-0002', 2, 2, '2025-09-12', 600.00, 'cash', 'REC-0012', 'posted', 1, NOW(), 1, NOW())
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 15. RESET POSTGRESQL SEQUENCES
-- ------------------------------------------------------------------------------
SELECT setval('university_academic_year_id_seq', (SELECT MAX(id) FROM university_academic_year));
SELECT setval('university_semester_id_seq', (SELECT MAX(id) FROM university_semester));
SELECT setval('university_classroom_id_seq', (SELECT MAX(id) FROM university_classroom));
SELECT setval('university_faculty_id_seq', (SELECT MAX(id) FROM university_faculty));
SELECT setval('university_department_id_seq', (SELECT MAX(id) FROM university_department));
SELECT setval('university_program_id_seq', (SELECT MAX(id) FROM university_program));
SELECT setval('university_teacher_id_seq', (SELECT MAX(id) FROM university_teacher));
SELECT setval('university_subject_id_seq', (SELECT MAX(id) FROM university_subject));
SELECT setval('university_academic_assignment_id_seq', (SELECT MAX(id) FROM university_academic_assignment));
SELECT setval('university_class_section_id_seq', (SELECT MAX(id) FROM university_class_section));
SELECT setval('university_student_id_seq', (SELECT MAX(id) FROM university_student));
SELECT setval('university_enrollment_id_seq', (SELECT MAX(id) FROM university_enrollment));
SELECT setval('university_fee_id_seq', (SELECT MAX(id) FROM university_fee));
SELECT setval('university_fee_line_id_seq', (SELECT MAX(id) FROM university_fee_line));
SELECT setval('university_payment_id_seq', (SELECT MAX(id) FROM university_payment));

COMMIT;
