# University School Management System (Odoo 19.0)

**Module:** `school_management`  
**License:** LGPL-3  
**Category:** Education / University Management  
**Primary Student Portal Controller:** [student_dashboard_shell.js](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/student_dashboard_shell.js)  
**Detailed Technical Specification:** [student_dashboard_shell.md](file:///C:/Odoo/odoo/custom/school_management/document/student_dashboard_shell.md)  

---

## 1. Overview

The **University School Management System** is an enterprise-grade academic ERP designed for higher education institutions operating on Odoo 19.0. It provides end-to-end management of university students, academic departments, faculties, degree programs, class sections, recurring timetable schedules, multi-criteria grading policies, transcripts, classroom logistics, tuition billing, and campus communications.

At the core of the learner experience is the **Student Dashboard Shell** (`student_dashboard_shell.js`), an interactive Single Page Application (SPA) built with Odoo OWL 2 and Chart.js.

---

## 2. Student Dashboard Shell (`student_dashboard_shell.js`)

The file located at [static/src/school_management/student_dashboard_shell.js](file:///C:/Odoo/odoo/custom/school_management/static/src/school_management/student_dashboard_shell.js) serves as the primary controller for the student academic portal (`action_student_dashboard_shell`).

### 2.1 Key Technical Capabilities

- **OWL 2 Component Framework:** Extends `Component` from `@odoo/owl` using `useState()`, `onWillStart()`, `onMounted()`, `onWillUnmount()`, and `useRef()`.
- **Asynchronous Asset & Data Pipeline:**

  - Loads the `web.chartjs_lib` JavaScript asset bundle dynamically during `onWillStart()`.
  - Concurrently queries the backend dashboard engine (`school.dashboard.get_student_dashboard_data`) and the student's personal academic records via Odoo ORM (`useService("orm")`).

- **Administrative Staff Preview Mode:**

  - Automatically identifies whether an active session belongs to academic staff (`group_school_teacher`, `group_school_admin`, `group_school_registrar`, `group_school_hod`, `group_school_dean`).
  - If a staff member or administrator does not have a linked student record, the shell automatically engages **Preview Mode**, displaying a top banner and student switcher dropdown with up to 20 active students.

- **Visual Analytics with Chart.js:**

  - **Weekly Attendance Trend (Line Chart):** Features cubic Bézier smoothing (`tension: 0.4`), gradient fills, and custom percentage tooltips.
  - **Attendance Status (Doughnut Chart):** Displays present, late, absent, and excused distributions with a 75% cutout and a custom canvas plugin (`doughnutCenterText`) drawing centered KPI percentages.

- **Timetable Scheduling & Countdown Engine:**

  - Computes the Monday–Sunday active calendar week.
  - Queries `university.timetable.slot.get_schedule(startStr, endStr, filters)`.
  - Determines slot status (`live`, `upcoming`, `completed`, `cancelled`) and renders live countdowns (e.g., `"Starts in 25 min"`).

- **Academic Self-Service & Document Generation:**

  - **Class Roster CSV Export:** Client-side CSV generation downloading enrolled classes (`My_Classes_{StudentID}.csv`).
  - **Official Transcript Requests:** Wizard modal launcher for `university.transcript.request`.
  - **Official Curriculum & Transcript PDFs:** Triggers QWeb PDF generation via `ir.actions.report`.
  - **Absence Excuse Submissions:** In-component modal dialog submitting excuses directly for academic review.

For complete line-by-line documentation, state variable schemas, and architecture diagrams, see [student_dashboard_shell.md](file:///C:/Odoo/odoo/custom/school_management/document/student_dashboard_shell.md).

---

## 3. Directory Layout

```text
custom/school_management/
├── controllers/          # Web and portal HTTP controllers (/my/student/dashboard)
├── data/                 # System sequences, grading policies, and configuration data
├── demo/                 # Academic demo data (students, teachers, courses, schedules)
├── document/             # Architectural specifications, BRDs, and guides
│   ├── student_dashboard_shell.md      # Full technical guide for student_dashboard_shell.js
│   ├── student_role_features.md        # Student security, permissions, and features
│   └── project_overview.md             # High-level architecture overview
├── models/               # Backend Python models (ORM)
│   ├── student.py        # university.student
│   ├── dashboard.py      # school.dashboard
│   ├── classroom.py      # university.classroom
│   ├── timetable_slot.py # university.timetable.slot
│   └── ...
├── reports/              # QWeb PDF report templates (transcripts, curriculum, receipts)
├── security/             # ir.model.access.csv and ir.rule record access security
├── static/               # Frontend assets
│   └── src/school_management/
│       ├── student_dashboard_shell.js   # Student portal OWL controller
│       ├── student_dashboard_shell.xml  # Student portal QWeb template
│       ├── student_dashboard_shell.scss # Student portal styles & themes
│       ├── teacher_dashboard_shell.js   # Teacher portal OWL controller
│       └── dashboard_shell.js           # Administrative dashboard controller
└── views/                # Odoo XML action and menu definitions
```

---

## 4. Key Security Groups & Access Boundaries

- `school_management.group_school_student`: University Student (Read-only on master records, row-isolated access to own profile, enrollment, timetable, grades).
- `school_management.group_school_teacher`: Faculty / Instructor (Class section grading, session attendance recording, advising notes).
- `school_management.group_school_registrar`: Academic Registrar (Enrollments, official transcript approvals, graduation clearances).
- `school_management.group_school_admin`: School Administrator (Full system configuration, timetable generation, user management).
