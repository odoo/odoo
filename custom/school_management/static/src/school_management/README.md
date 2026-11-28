# School Management Frontend Assets (`static/src/school_management`)

This directory houses the OWL (Odoo Web Library) single-page application shells and frontend styling for the `school_management` module.

---

## 1. Student Dashboard Shell (`student_dashboard_shell.js`)

**Target File:** [student_dashboard_shell.js](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/student_dashboard_shell.js)  
**Detailed Guide:** [document/student_dashboard_shell.md](file:///C:/Odoo/odoo/custom/school_management/document/student_dashboard_shell.md)  
**Action XML ID:** `school_management.action_student_dashboard_shell`  
**OWL Registry Key:** `student_dashboard_shell`  

### Overview & Core Modules
### Modern University Student Portal Redesign
The Student Dashboard features a modern responsive two-column portal layout:
- **Hero Welcome Banner**: Greeting, squircle avatar with `Enrolled [X]` badge, active semester tag.
- **5 Elevated KPI Cards**: Enrolled Courses, Attendance %, Cumulative GPA (Dean's list badge), Fee Balance (payment status), and Library Loans (due badge).
- **Left Column (~65% width) — My Class Schedule**:
  - Period navigation (`< > Today`) and dynamic date heading (`Nov 2 – 8, 2026`).
  - View Switcher: `[ Week | Month | List ]` pill buttons (`#7c3aed`).
  - **Week View**: 7 columns (MON-SUN), 08:00–18:00 time markers, cards positioned by start/end times with course code, title, time, room, instructor, and subject color classes.
  - **Month View**: 42 calendar grid cells, daily session badges, today highlight.
  - **List View**: Chronological agenda with date badge, time, course info, and status.
- **Right Column (~35% width)**:
  - **My Transcript**: Top 4 academic results from `university.transcript.line` (Course, Credits, Grade, Status) + `View Full Transcript →`.
  - **Quick Actions (2x2 Grid)**: View Schedule, Course Details, Fee Payment, Library Portal.
- **Security**: Strictly derives student profile from authenticated `env.user.id`.


`student_dashboard_shell.js` is an OWL 2 component providing the full-featured **Student Academic Portal**.

- **Template:** `school_management.StudentDashboardShell` defined in [student_dashboard_shell.xml](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/student_dashboard_shell.xml).
- **Styling:** [student_dashboard_shell.scss](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/student_dashboard_shell.scss).
- **Chart.js Visualizations:** Dynamically loads `web.chartjs_lib` for attendance trend (line chart) and session distribution (doughnut chart with inline `doughnutCenterText` plugin).
- **Data Ingestion:**
  - `loadDashboardData()`: Aggregated analytics from `school.dashboard.get_student_dashboard_data`.
  - `loadStudentData()`: Profile, enrollments, classrooms, timetable slots (`get_schedule`), attendance metrics, transcripts, and curriculum.
- **Administrative Preview Mode:** Automatically activates for teachers and administrators when no student record is directly attached to the session user, allowing role-based testing.
- **Client Utilities:**
  - CSV export of enrolled classes (`downloadClassesList`).
  - Absence excuse submission dialog (`openExcuseModal`, `submitExcuse`).
  - Syllabus viewer modal (`openSyllabusModal`).
  - Dynamic status countdowns (`"Starts in 15 min"`).

---

## 2. Companion Frontend Files in this Directory

| File Name | Purpose |
| :--- | :--- |
| [student_dashboard_shell.js](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/student_dashboard_shell.js) | Main OWL 2 component controller for the Student Portal. |
| [student_dashboard_shell.xml](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/student_dashboard_shell.xml) | QWeb XML template defining student identity card, metrics, timetable, modals, and charts. |
| [student_dashboard_shell.scss](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/student_dashboard_shell.scss) | SCSS stylesheets for student portal typography, layout grids, cards, and animations. |
| [teacher_dashboard_shell.js](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/teacher_dashboard_shell.js) | Teacher / Faculty portal controller for daily teaching schedule and session attendance. |
| [dashboard_shell.js](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/dashboard_shell.js) | Executive / School Administrator operational dashboard controller. |
| [webclient_patch.js](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/webclient_patch.js) | WebClient patches for top navigation bar and portal breadcrumbs. |
