python odoo-bin -c odoo.conf -d odoo -u school\_management



***Role Verification \& Test Checklist***

The visibility rules and hierarchy were verified against database odoo using Odoo's web client menu loader (ir.ui.menu.load\_menus()):

Role Tested

Exact Top Bar Items

Verified Submenus \& Sections Prohibited / Hidden Items ConfirmedStatus

**Student**

&#x20;  Dashboard, Schedule, My Learning, My Records, My Fees, My Profile, Notice Board

• My Learning: My Classes, My Assignments, My Submissions, Attendance, Classrooms

• My Records: My Transcript, Report Cards, Transcript RequestsTeacher Dashboard, Academic Setup, Teaching \& Learning, Results, People, Admissions, Finance, Administration



**Teacher**

&#x20; Dashboard, Teacher Dashboard, Schedule, Academic Setup, Teaching \& Learning, Results, People, Notice Board

• Schedule: My Timetable, Timetable, Holidays, Classrooms

• Academic Setup: Curriculum Subjects

• Teaching \& Learning: Classes, Attendance, Coursework, Exams

• Results: Assessment Results

• People: Students, Academic Staff, Student Advising

Student learning dropdowns, Generate Timetable, Timeslots, Leadership, Staff Attendance, Admissions, Finance, Administration



**Head of Department (HOD)**

&#x20; Dashboard, Teacher Dashboard, Schedule, Academic Setup, Teaching \& Learning, Results, People, Admissions \& Enrollment, Notice Board

• Academic Setup: Structure Departments; Calendar  Department Terms, Terms Ending Soon; Curriculum Subjects

• People: Leadership Heads of Department, Role Assignments

• Admissions \& Enrollment: Enrollment

Faculties, Academic Years, Semesters, Grading, Heads of Faculty, Staff Attendance, Bulk Enrollment, Add Students to Class, Finance, Administration



**Head of Faculty (Dean)**

&#x20;Dashboard, Teacher Dashboard, Schedule, Academic Setup, Teaching \& Learning, Results, People, Admissions \& Enrollment, Notice Board

Same as HOD + Structure  Programs and Leadership  Heads of Faculty

Faculties, Academic Years, Semesters, Grading, Staff Attendance, Bulk Enrollment, Add Students to Class, Finance, Administration



**Registrar (Standalone)**

&#x20;   Dashboard, Schedule, Academic Setup, Results, People, Admissions \& Enrollment

• Schedule: Holidays

• Academic Setup: Calendar  Department Terms, Terms Ending Soon

• Results: Transcripts, Transcript Requests

• People: Students

• Admissions \& Enrollment: Enrollment, Bulk Enrollment

Teacher Dashboard, Structure, Curriculum, Grading, Teaching \& Learning, Leadership, Staff Attendance, Finance, Administration



**Administrator / Manager**

&#x20;Dashboard, Teacher Dashboard, Schedule, Academic Setup, Teaching \& Learning, Results, People, Admissions \& Enrollment, Finance, Administration, Notice Board

Full system access across all 8 subcategories and 42 distinct actions

