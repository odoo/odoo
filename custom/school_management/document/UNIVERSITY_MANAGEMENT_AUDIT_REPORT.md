# University Management System — Full Codebase Audit Report

**Project:** Harvard University ERP (Odoo 19)
**Audit date:** 2026-11-18
**Branch audited:** `harvard_university`
**Audit type:** Complete static codebase audit (read-only)
**Status:** Awaiting review and approval — **no code was modified**

---

## Table of Contents

1. [Methodology & Scope](#1-methodology--scope)
2. [Executive Summary](#2-executive-summary)
3. [Part 2 — Feature Audit Table](#3-part-2--feature-audit-table)
4. [Part 3 — Missing Features](#4-part-3--missing-features)
5. [Part 4 — Incomplete Features](#5-part-4--incomplete-features)
6. [Part 5 — Integration Problems](#6-part-5--integration-problems)
7. [Part 6 — Security Audit](#7-part-6--security-audit)
8. [Part 7 — Recommended Architecture](#8-part-7--recommended-architecture)
9. [Part 8 — Implementation Roadmap](#9-part-8--implementation-roadmap)
10. [Verification Caveats](#10-verification-caveats)
11. [Appendix A — Model Inventory](#11-appendix-a--model-inventory)
12. [Appendix B — Module Inventory](#12-appendix-b--module-inventory)

---

## 1. Methodology & Scope

### 1.1 Modules inspected

| Module | Files | Size | Status |
|---|---|---|---|
| `custom/school_management` | 425 | 25 MB | Core — primary audit target |
| `custom/school_eLearning` | 12 | 72 KB | Integration bridge to `website_slides` |
| `custom/school_purchase` | 22 | 386 KB | Book procurement bridge |
| `custom/school_public_holiday` | 44 | 925 KB | Holiday calendar |
| `custom/school_website` | 32 | 1.5 MB | Public website + chatbot |
| `custom/school_crm` | 1 | 0 | **EMPTY — no manifest** |
| `custom/school_inventory` | 1 | 0 | **EMPTY — no manifest** |

### 1.2 Verified artefacts per module

- `models/` — all Python model definitions, fields, computes, constraints, business methods, state transitions
- `views/` — all form / list / kanban / search / calendar / gantt views, menus, window actions, buttons
- `wizard/` — all transient models + their views
- `security/` — `ir.model.access.csv`, `record_rules.xml`, `res.groups`
- `data/` — sequences, cron jobs, mail templates, defaults
- `report/` / `reports/` — QWeb PDF templates + `ir.actions.report` records
- `controllers/` — HTTP/JSON-RPC routes, portal routes, auth levels
- `static/` — OWL components and their `registry.category("actions")` registrations
- `demo/` — demo data
- `tests/` — test files and their `__init__.py` wiring
- `__manifest__.py` / `__init__.py` — dependency graph and load order

### 1.3 Verification techniques applied

| Check | Technique | Result |
|---|---|---|
| Model → ACL coverage | Parsed all 319 ACL rows, normalised `model_x_y` → `x.y` | 63/63 real models covered |
| View → model existence | Every `<field name="model">` in `ir.ui.view` records resolved against `_name` declarations | 0 orphan view models |
| Button → method existence | Every `<button type="object" name="…">` matched against a `def` in the target model | **0 missing methods** |
| View field → field definition | Fields used in outer view archs matched against `fields.*` declarations | Reviewed; nested sub-view fields excluded |
| Menu → action existence | Every `<menuitem action="…">` resolved | 1 false positive (server action), 1 cross-module action |
| XML ID references | All `ref="…"` / `%(… )d` resolved against declared records | 36 unresolved — 19 legitimate (`model_*`, menus defined later), 8 demo data, remainder benign |
| Client action → JS registration | Every `ir.actions.client` tag matched in `static/src/**/*.js` | **11/11 registered** |
| Sequence usage | Every `next_by_code("…")` matched against an `ir.sequence` record | **3 missing** |
| Module integrity | Manifest presence, `data` load order, dependency closure | 2 modules empty, 1 dead file |

### 1.4 Scale metrics (verified)

```
Model classes ...................... 66
View records (ir.ui.view) .......... 225
Window actions ..................... 117
ACL rows ........................... 319
Record rules ....................... 30+ (across 9 files)
Security groups .................... 14
Test files ......................... 29
Test methods ....................... 264  (all wired in tests/__init__.py)
Client (OWL) actions ................ 11  (all registered)
QWeb PDF reports .................... 6
Cron jobs .......................... 5
```

### 1.5 Status vocabulary

| Status | Definition |
|---|---|
| **IMPLEMENTED** | Model + fields + views + ACL + working business logic verified |
| **PARTIALLY IMPLEMENTED** | Exists but has a functional gap (unreachable state, missing view, missing report, missing guard) |
| **MISSING** | No implementation found |
| **BROKEN** | Exists but currently errors or does not perform its stated function |
| **DUPLICATED** | Similar functionality implemented in more than one place |
| **NEEDS VERIFICATION** | Static evidence insufficient — requires a live DB / test run |

> **Governing rule applied:** a feature is not marked IMPLEMENTED merely because its model or view exists. Every IMPLEMENTED classification below is backed by a verified call path from a button or cron to a Python method that performs the work.

---

## 2. Executive Summary

### 2.1 Totals

| Metric | Count | % |
|---|---|---|
| Features audited | **89** | 100% |
| IMPLEMENTED | **65** | 73.0% |
| PARTIALLY IMPLEMENTED | **15** | 16.9% |
| MISSING | **7** | 7.9% |
| BROKEN | **1** | 1.1% |
| NEEDS VERIFICATION | **1** | 1.1% |
| Duplicated clusters (cross-cutting) | 3 | — |

### 2.2 Headline findings

**Critical**

1. **Two modules are empty shells.** `custom/school_crm/` and `custom/school_inventory/` contain only `__init__.py` and **no `__manifest__.py`** — they cannot be installed. Any CRM or standalone Inventory feature is therefore MISSING.

2. **No accounting integration exists.** Zero references to `account.move`, `account.payment`, `account.journal` or `account.account` anywhere in the codebase. `account` is **not** in `__manifest__.py` `depends`. Finance is a fully custom ledger (fee → payment → balance) with **no general ledger, no journal entries, no trial balance**. `university.payment.action_post()` (`models/finance/payment.py:119`) only flips a custom state field.

3. **IDOR vulnerability on dashboard RPCs.** `school.dashboard.get_student_dashboard_data()` and `get_teacher_dashboard_data()` accept an arbitrary `student_id` / `teacher_id` supplied by the caller and `sudo().browse()` it with **no ownership check**, then fall back to "first student in the database" (`models/dashboard/dashboard.py:1218-1230`, `1605-1618`). The JSON-RPC route is `auth="user"` (`controllers/dashboard/dashboard.py:10`).

4. **Enrollment approval workflow is cosmetic.** The `to_approve` and `withdrawn` statuses are unreachable, and `action_approve()` simply delegates to `action_confirm()` (`models/enrollment/enrollment.py:388-396`).

5. **eLearning constraint crashes and its security file is dead.** `school_eLearning/models/slide_channel.py:43` reads `subject_id` on a `university.teacher` record (the teacher model defines `subject_ids`), and `school_eLearning/security/ir.model.access.csv.py` is a mis-extensioned file never loaded by the manifest.

**Positive**

6. **Security coverage is significantly better than typical Odoo customisations.** All 63 real models have ACLs; per-model record rules exist for student / teacher / HOD / Dean / Registrar scopes (`security/people/record_rules.xml`, `security/enrollment/record_rules.xml`, `security/grading/record_rules.xml`, `security/attendance/record_rules.xml`, `security/finance/record_rules.xml`); academic-year locking (`models/academic/academic_lock.py`) is consistently enforced on grades, report cards, holidays and enrollments.

7. **All 11 OWL client actions are registered**, all 6 QWeb PDF reports exist and are bound, and **264 test methods are wired** into the test runner.

8. **All object-type buttons resolve to real Python methods** — a clean result that most hand-built Odoo modules fail.

### 2.3 Risk heat map

| Severity | Count | Domains |
|---|---|---|
| **P0 — Critical** | 7 | Security (IDOR, rule overlap), eLearning crash, dead modules |
| **P1 — High** | 6 | Enrollment approval, attendance approval, grading sync, sequences, accounting |
| **P2 — Medium** | 6 | eLearning lifecycle, documents, discipline, admission stages, finance reports |
| **P3 — Low** | 6 | Room availability UI, orphan wizard, HOD scopes, multi-company, dev artefacts |

---

## 3. Part 2 — Feature Audit Table

**Column legend:** **Py** = Python implementation, **XML** = views/menus/actions/buttons, **Sec** = ACL + record rules, **Biz** = business logic (state machine, validation, integration). ✅ full · ◐ partial · ✗ none.

### 3.A Academic Management

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Faculty Management | `university.faculty` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `models/academic/faculty.py` (136 L), form/list/kanban, `tests/academic/test_faculty.py` |
| Department Management | `university.department` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | HOD link + record rules present |
| Program Management | `university.program` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `models/academic/program.py` (189 L) |
| Academic Year | `university.academic.year` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | State machine + `current` flag + rollover wizard + lock enforcement |
| Semester Management | `university.semester` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `models/academic/semester.py` (456 L) |
| Department Term (academic calendar) | `university.department.term` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Registration / add-drop / exam / grade windows; `tests/academic/test_department_term.py` |
| Subject Management | `university.subject` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `models/academic/subject.py` (220 L) |
| Semester Subjects (offerings) | `university.semester.subject` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `models/academic/semester_subject.py` (189 L) + `tests/academic/test_semester_subject.py` |
| Class Section | `university.class.section` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `models/academic/class_section.py` (752 L) + `tests/academic/test_class_section_access.py` |
| Classroom Management | `university.classroom` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Capacity + kanban UI |
| Room Availability | `university.room.availability` | ◐ | ✗ | ✅ | ◐ | **PARTIALLY IMPLEMENTED** | `models/academic/room_availability.py` (43 L) has **no views and no menu** — only consumable programmatically by the timetable engine |
| Academic Assignment | `university.academic.assignment` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Teacher ↔ subject ↔ department mapping |
| Lesson Plans | `university.lesson.plan` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Teacher record rule + submit/approve |
| Timetable Management | `university.timetable.slot` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `models/academic/timetable.py` (2,425 L), Gantt OWL view, generation wizard, `tests/academic/test_timetable_generation.py` |
| Timetable Conflicts | `university.timetable.conflict` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Kanban / list / form / search + `action_university_schedule_conflicts` server action |
| Curriculum | `university.curriculum` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Model + lines + PDF report `curriculum_report.xml` |
| Course Registration | `university.course.registration` | ◐ | ✅ | ✅ | ◐ | **PARTIALLY IMPLEMENTED** | **No `ir.sequence` record** for `university.course.registration`; falls back to `REG-YYYYMMDD` (`course_registration.py:106`) — potential duplicates |
| Course Evaluation | `university.course.evaluation` | ✅ | ✅ | ✅ | ? | **NEEDS VERIFICATION** | 225-line model + views + ACL exist; results consumption path not statically confirmed |
| Academic Lock Guard | `models/academic/academic_lock.py` | ✅ | n/a | n/a | ✅ | **IMPLEMENTED** | Enforced by grading, report cards, holidays, enrollment, assessment results |

### 3.B Student Management

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Student Registration | `university.student` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Sequence `university.student`, portal signup, `tests/people/test_student_signup.py` |
| Student Profiles | `university.student` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | 986 lines; computed GPA, attendance rate, risk level, fee balance |
| Admission Management | `university.admission.application` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | submit → approve → confirm → student + enrollment + fee (`admission.py:358-460`), `tests/admission/test_admission_fee.py` |
| Admission Stages | `admission.stage` | ◐ | ✗ | ✅ | ◐ | **PARTIALLY IMPLEMENTED** | Model `models/admission/admission_stage.py` + ACL exist but **no views, no menu**, and the application state machine does not reference stages |
| Admission Leads | `admission.lead` | ✅ | ✅ | ✅ | ◐ | **PARTIALLY IMPLEMENTED** | Model + views + ACL present; **no automated lead → application conversion action found** |
| Student Enrollment | `university.enrollment` | ◐ | ✅ | ✅ | ◐ | **PARTIALLY IMPLEMENTED** | See below |
| Enrollment Approval | *(state machine)* | ✗ | ✗ | ✗ | ✗ | **BROKEN** | `status` declares `to_approve` and `withdrawn` but **neither is ever set**; `action_approve()` is an alias for `action_confirm()` (`enrollment.py:391-392`). No registrar approval gate, no rejection reason, no requester/approver separation |
| Student Documents | — | ✗ | ✗ | — | ✗ | **MISSING** | No document/attachment vault on `university.student`; only fee-scoped signatures exist |
| Student Status Management | `university.student.status` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | active / graduated / suspended etc., with transitions |
| Student Portal | portal controller + templates | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | 4 routes (`/my/student/dashboard`, `/my/student/transcript/request`, `/my/books`, counters); ownership resolved server-side (`controllers/portal/student_portal.py:39-54`) |
| Student Dashboard | `school.dashboard` + OWL shell | ✅ | ✅ | ✗ | ✅ | **IMPLEMENTED** | Fully functional — but see **IDOR** in §7.1 |
| Advising | `university.student.advising.note` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Category / note / follow-up |
| Student Change Requests | `university.student.change.request` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Missing sequence → `REQ-YYYYMMDD` fallback (`student_change_request.py:81`) |
| Follow-ups | `university.student.followup` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Registrar / HOD / Dean / teacher / student rules |

### 3.C Teacher Management

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Teacher Profiles | `university.teacher` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `models/people/teacher.py` (715 L) + account provisioning wizard |
| Teacher Dashboard | OWL + `school.dashboard` | ✅ | ✅ | ◐ | ✅ | **IMPLEMENTED** | Functional; IDOR via `teacher_id` param (§7.1) |
| Teacher Class Assignment | `university.class.section.teacher_id`, `university.academic.assignment` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Managed scopes tested in `tests/people/test_teacher_managed_scopes.py` |
| Teaching Schedule | `university.timetable.slot` + Gantt | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `action_university_timetable_slot_teacher` |
| Attendance Recording | `university.attendance.session` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Teacher record rules + `_allowed_edit` guard |
| Assignment Management | `university.assignment(+.submission)` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | 486 lines; auto-grade hook + deadline cron |
| Lesson Plan Management | `university.lesson.plan` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | — |
| Grading Management | `university.assessment.result`, `university.exam.score` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Teacher write scoped by section |
| Teacher Attendance (own) | `university.staff.attendance` | ✅ | ✅ | ◐ | ✅ | **PARTIALLY IMPLEMENTED** | ACL has **no `group_school_teacher` row** although a teacher record rule exists (`security/attendance/record_rules.xml:75`) → teachers get `AccessError` and the rule is unreachable |

### 3.D Attendance Management

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Student Attendance (lines) | `university.attendance` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | 1,443-line file; per-section rules; `tests/attendance/test_attendance_sheet.py` |
| Attendance Session / Sheet | `university.attendance.session` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Unique (section, date) constraint; auto line sync; OWL sheet registered at `attendance_sheet.js:665` |
| Attendance Workflow (draft → submitted → approved → rejected) | session `state` | ✗ | ✗ | — | ✗ | **PARTIALLY IMPLEMENTED** | Only `draft` / `recorded` (`attendance.py:48-53`). **No submit, approve or reject step** for student attendance |
| Staff Attendance | `university.staff.attendance` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | 587 lines; submit/approve/reject/cancel (`staff_attendance.py:234-262`), `tests/attendance/test_staff_attendance.py` |
| Attendance Reports | client action `university_attendance_reports` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Registered at `attendance_reports.js:12` |
| Attendance Statistics / Grid | `university_attendance_grid` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `attendance_grid.js:291` |
| At-Risk Attendance | `university_attendance_at_risk` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `attendance_at_risk.js:222` |
| Attendance Comparison | `university_attendance_comparison` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `attendance_comparison.js:275` |
| Holiday Management | `university.holiday` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Date-range CHECK constraint + within-year validation + academic lock |
| Public Holiday (Cambodia) | `public.holiday` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Khmer names, import log, notice auto-publish, session count |
| Holiday Import | `wizard.import.public.holiday` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | CSV/file import wizard + log model |
| Session Reschedule | `wizard.reschedule.session` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Triggered by holiday collisions |

### 3.E Examination & Grading

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Assessment Categories | `university.assessment.category` | ✅ | ✅ | ✅ | ◐ | **IMPLEMENTED** | Weight-sum-to-100 constraint validates **globally on every write** (`grading.py:149-158`) — brittle but functional |
| Assessment Results | `university.assessment.result` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Score bounds, period consistency, academic-year lock |
| Examination Management | `university.exam` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | 850 lines: schedule → open → close → grading → publish → cancel; auto-close cron |
| Exam Scores | `university.exam.score` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Late penalty computation, absence flag, bounds validation |
| Exam Marksheet | `reports/grading/exam_marksheet_report.xml` + 2 controllers | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | QWeb PDF + XLSX generation |
| Grade Calculation | `university.report.card.action_generate_lines` | ✅ | ✅ | ✅ | ◐ | **IMPLEMENTED** | Weighted component aggregation; see gap below |
| GPA Calculation | `university.report.card.gpa`, `university.transcript.cumulative_gpa` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Credit-weighted, repeat-course handling, Dean's List thresholds via `ir.config_parameter` |
| Academic Results | `university.report.card` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | draft → generated → approved + verification code |
| Transcript | `university.transcript` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | QWeb PDF `report_university_transcript_document` + XLSX |
| Transcript Requests | `university.transcript.request` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Holds (fees/status), payment state, approve/reject/issue/deliver, override + reject wizards, `tests/grading/test_transcript_request.py` |
| Grade Reports | report card PDF + marksheet | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | — |

> **Grade calculation gap:** `grading.py:479-483` builds the attendance domain from `subject_sections`; when a subject has no matching section, the domain collapses to student-only and pulls **attendance from all semesters**. Should be scoped by `academic_year_id` + `semester_id`.

### 3.F Finance Management

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Fee Management | `university.fee` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | 531 lines; draft/posted/paid/canceled; `payment_state` compute with overdue detection |
| Fee Structure | `university.fee.structure` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Lines + `_prepare_fee_vals()` |
| Student Payments | `university.payment` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Overpayment constraint, student/fee consistency, state edit lock, `tests/finance/test_payment.py` |
| Payment Receipts | QWeb `payment_report.xml` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Email on full payment via `mail_template.xml` |
| Outstanding Fees | computed `payment_state` / `is_overdue` / `days_overdue` | ◐ | ◐ | ✅ | ◐ | **PARTIALLY IMPLEMENTED** | Flags exist and are indexed, but there is **no aging report** and no consolidated student statement |
| Payment History | payment list + portal | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Student sees own payments via record rule |
| Financial Reports | `payment_report.xml` only | ◐ | ◐ | ✅ | ◐ | **PARTIALLY IMPLEMENTED** | Single payment document; **no revenue-by-period, collection-rate or reconciliation report** |
| Accounting Integration | — | ✗ | ✗ | — | ✗ | **MISSING** | No `account.move` / `account.payment`; `account` not a dependency; no GL posting anywhere |
| Payment Reminders | `university.fee.action_send_payment_reminder` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `reminder_count` / `last_reminder_date` tracking |

### 3.G University eLearning

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Course Management | `slide.channel` (inherit) | ◐ | ✅ | ◐ | ◐ | **PARTIALLY IMPLEMENTED** | Native `website_slides` forms reused; **broken constraint** (§6.1) |
| Course Categories | native `slide.channel.tag` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Provided by `website_slides` — correctly **not duplicated** |
| Academic Subject Integration | `slide.channel.subject_id` | ✅ | ✅ | ◐ | ✅ | **IMPLEMENTED** | Inverse `university.subject.slide_channel_ids` + stat button |
| Instructor Assignment | `slide.channel.teacher_id` | ◐ | ✅ | ◐ | ◐ | **PARTIALLY IMPLEMENTED** | Field + onchange exist; constraint crashes on the teacher model |
| Class Section Link | `slide.channel.class_section_id` | ◐ | ✅ | ◐ | ◐ | **PARTIALLY IMPLEMENTED** | Inverse `class_section.slide_channel_ids` + stat button; validation logic defective |
| Course Enrollment | — | ✗ | ✗ | — | ✗ | **MISSING** | No bridge from `university.enrollment` to `slide.channel.member` |
| Learning Progress | — | ✗ | ✗ | — | ✗ | **MISSING** | No sync between `slide.slide.partner` and academic records |
| Completion & Certificates | — | ✗ | ✗ | — | ✗ | **MISSING** | Native completion exists but never writes back credits/standing |
| Learning Reports | — | ✗ | ✗ | — | ✗ | **MISSING** | No academic ↔ eLearning analytics |
| eLearning Security | `security/ir.model.access.csv.py` | ✗ | — | ✗ | — | **BROKEN** | File has `.py` extension so **Odoo never loads it**; it also references a non-existent `model_school_subject` |

### 3.H Student Services

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Service Hours | `university.service.hour` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Pending/approved/rejected + approval access check |
| Service Requests | `university.service.request` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Missing sequence → timestamp fallback (`service_request.py:107`) |
| Discipline Management | — | ✗ | ✗ | — | ✗ | **MISSING** | Only an advising-note **category label** "Attendance & Discipline" (`advising.py:39`); no incident/case/sanction model |
| Notice Board | `university.notice.board` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `target_audience`, priority, pinned, department, academic year |
| Announcements (public site) | notice board via website | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `/events` controller (`school_website/controllers/dashboard/events.py:7`) |
| Document Signature | `university.document.signature` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Fee-scoped only; `tests/core/test_document_signature.py` |
| Document Download (PDF/XLSX) | `university.document.download.mixin` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | State gate + group gate + download log |

### 3.I Administration & Configuration

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| User Management | `res.users` (inherit) | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `models/people/res_users.py` |
| Role / Group Management | 14 `res.groups` | ✅ | ✅ | ✅ | ◐ | **IMPLEMENTED** | `group_school_teacher` declared **twice** with a circular implication (§7.3) |
| Administrator role | `group_school_admin` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Implies registrar + timetable manager + `base.group_system` |
| Registrar role | `group_school_registrar` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Broad read/write on academic + finance |
| HOD role | `group_school_hod` | ✅ | ✅ | ◐ | ✅ | **IMPLEMENTED** | Department-scoped rules present for students/enrollments/attendance; **missing for timetable slots** |
| Dean role | `group_school_dean` | ✅ | ✅ | ◐ | ✅ | **IMPLEMENTED** | Faculty-scoped rules present; same timetable gap |
| Teacher role | `group_school_teacher` | ✅ | ✅ | ◐ | ✅ | **IMPLEMENTED** | Strong rules; ACL gap on staff attendance |
| Student role | `group_school_student` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Own-records-only rules across all domains |
| System Settings | `res.config.settings` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Dean's-list thresholds via `ir.config_parameter` + `tests/core/test_settings.py` |
| Access Control Lists | 319 rows / 10 files | ✅ | n/a | ✅ | ✅ | **IMPLEMENTED** | All 63 real models covered |
| Record Rules | 30+ `ir.rule` | ✅ | n/a | ◐ | ◐ | **PARTIALLY IMPLEMENTED** | Duplicate / overlapping rules — see §7.2 |
| Capabilities | `university.capability` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Data-driven capability registry |
| Multi-company | `company_id` fields | ◐ | ◐ | ✗ | ◐ | **PARTIALLY IMPLEMENTED** | Fields on fee / payment / assessment only; **no company record rules**, little `check_company` |

### 3.J Procurement & Inventory

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Book Requirements | `university.book.requirement` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Unique (section, subject) constraint, quantity validation, `tests/procurement/test_book_procurement.py` |
| Purchase Requests / RFQs | `purchase.order` (inherit) | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Vendor grouping, stock-aware quantities, mutable-RFQ guards |
| Book Procurement | class section action | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `action_university_class_section_missing_books` |
| Subject-to-Book Relationship | `university.subject.book` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `product.template.is_textbook` + constraint + migration helper |
| Enrollment-to-Purchase Workflow | section aggregates | ◐ | ✅ | ✅ | ◐ | **PARTIALLY IMPLEMENTED** | Uses aggregate student counts only; **no per-student allocation / issue record** |
| Inventory Integration | `stock.quant` reads | ◐ | ◐ | ◐ | ◐ | **PARTIALLY IMPLEMENTED** | Reads free quantity only; **`school_inventory` module is an empty stub**; no issue/return to students |

### 3.K Public Website (additional scope discovered)

| Feature | Model | Py | XML | Sec | Biz | Status | Missing components |
|---|---|---|---|---|---|---|---|
| Home / About / Contact / Jobs | `controllers/core/main.py` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `auth='public'`, `sudo()` reads |
| Courses Directory | `controllers/academic/courses.py` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | `/courses`, `/courses/<id>`, degree filter, sitemap |
| Online Admission | `controllers/admission/admission.py` | ✅ | ✅ | ◐ | ✅ | **IMPLEMENTED** | Creates application with current intake; see §7.4 (no rate limit) |
| Events / Notices | `controllers/dashboard/events.py` | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | Reads `university.notice.board` |
| AI Chatbot | `chatbot.script` (inherit) | ✅ | ✅ | ✅ | ✅ | **IMPLEMENTED** | OpenRouter / OpenAI / Gemini providers, university knowledge context, fallback to operator |

---

## 4. Part 3 — Missing Features

### 4.1 Accounting Integration

**What is missing**
No journal entries, no `account.move` invoices, no chart-of-accounts posting, no AR/AP, no financial statements.

**Why it matters**
`university.payment.action_post()` (`models/finance/payment.py:119-149`) only flips a custom `state` to `posted`, posts a chatter message and calls `fee._update_state_from_balance()`. There is no general ledger, so:
- No trial balance, balance sheet or income statement can be produced
- No auditable double-entry trail exists for any student payment
- No reconciliation with bank statements
- External auditors cannot verify revenue

**Which existing models should connect**
| Existing model | Should connect via |
|---|---|
| `university.fee` | Should generate an `account.move` of type `out_invoice` on `action_post()` |
| `university.payment` | Should generate an `account.payment` / partial reconciliation on `action_post()`, reverse on `action_cancel()` |
| `university.fee.structure.line` | Should reference an `account.account` (revenue account) per fee line |
| `res.company` | Journal assignment per company |

**Files/components to create**
```
custom/school_accounting/__manifest__.py         (depends: account, school_management)
custom/school_accounting/models/fee.py           (_inherit university.fee)
custom/school_accounting/models/payment.py       (_inherit university.payment)
custom/school_accounting/data/journals.xml
custom/school_accounting/views/fee_views.xml     (inherit: add move_id smart button)
migrations/…/post-migrate.py                     (backfill existing posted payments)
```

---

### 4.2 Student Document Vault

**What is missing**
No model, views, security or portal surface for student documents (transcripts, national ID, certificates, medical records, admission supporting files).

**Why it matters**
- Admission collects applicant data but stores no supporting documents
- `university.document.signature` is **fee-scoped only** (`fee_id` is its only business link)
- No document verification status, issue date, or expiry tracking
- Registrar cannot enforce "documents complete" before enrollment

**Which existing models should connect**
| Existing model | Relationship |
|---|---|
| `university.student` | `document_ids` One2many |
| `university.admission.application` | `document_ids` One2many (pre-registration uploads) |
| Portal `/my/student/dashboard` | document tab |

**Files/components to create**
```
custom/school_management/models/people/student_document.py     university.student.document
custom/school_management/views/people/student_document_views.xml
custom/school_management/security/people/ir.model.access.csv   (append rows)
custom/school_management/security/people/record_rules.xml       (student-own rule)
custom/school_management/views/portal/portal_templates.xml      (documents tab)
```

---

### 4.3 Discipline Management

**What is missing**
No incident/violation model, no case workflow, no sanction catalogue, no hearing record, no appeal path.

**Why it matters**
The only trace of discipline in the entire codebase is a *string label* — `("attendance", "Attendance & Discipline")` at `models/advising/advising.py:39` and a matching search filter at `views/advising/advising_views.xml:146`. A university cannot record, track or report disciplinary cases.

**Which existing models should connect**
| Existing model | Relationship |
|---|---|
| `university.student` | `discipline_case_ids` One2many |
| `university.enrollment` | sanctions may affect enrollment status |
| `university.notice.board` | publish anonymised outcomes |
| `school.dashboard` | discipline KPI tile |

**Files/components to create**
```
custom/school_management/models/discipline/discipline_case.py   university.discipline.case
custom/school_management/models/discipline/sanction.py          university.discipline.sanction
custom/school_management/views/discipline/discipline_views.xml
custom/school_management/security/discipline/ir.model.access.csv
custom/school_management/security/discipline/record_rules.xml
```

---

### 4.4 eLearning Course Enrollment Bridge

**What is missing**
No link between `university.enrollment` and `slide.channel.member`.

**Why it matters**
A student enrolled in a class section that has an eLearning channel is **not** automatically a channel member, so they cannot access course material without a manual, separate action. This defeats the purpose of the `class_section_id` relation added in `school_eLearning`.

**Which existing models should connect**
`university.enrollment` → `slide.channel.member` (via `class_section_id.slide_channel_ids`), and `university.student` → `slide.channel.partner`.

**Files/components to create**
```
custom/school_eLearning/models/slide_channel_member.py   (_inherit slide.channel.member, add student_id)
custom/school_eLearning/models/enrollment.py             (_inherit university.enrollment, action hooks)
```

---

### 4.5 eLearning Learning Progress Sync

**What is missing**
No synchronisation from `slide.slide.partner` (per-slide completion) into academic records, and no academic visibility of eLearning progress.

**Why it matters**
Instructors cannot see — inside the academic module — how much of the assigned eLearning course a student has completed. AGENTS.md §2.3 explicitly asks that standard `website_slides` be *extended*, not duplicated; today it is barely extended at all.

**Which existing models should connect**
`slide.slide.partner` / `slide.channel.partner` → `university.student`, `university.class.section` (progress column), `school.dashboard` (stat tile).

---

### 4.6 eLearning Completion → Academic Credit

**What is missing**
No rule that maps channel completion to a subject result, credit award or certificate issuance in the academic module.

**Why it matters**
An eLearning course tied to an academic subject should be able to contribute to that subject's assessment (e.g. a "practical" category) or mark the enrollment complete. Currently completion is isolated inside `website_slides`.

**Which existing models should connect**
`slide.channel.partner.is_completed` → `university.assessment.result` (category = practical) and/or `university.enrollment.status = completed`.

---

### 4.7 Learning Reports

**What is missing**
No report joining academic structure with eLearning activity.

**Why it matters**
No way to answer "how many students in CS101 completed the online module", "which channels have zero engagement", or "correlation between eLearning progress and grades".

**Files/components to create**
```
custom/school_eLearning/reports/learning_reports.xml
custom/school_eLearning/reports/learning_report_template.xml
custom/school_eLearning/views/learning_analytics_views.xml   (pivot + graph)
```

---

## 5. Part 4 — Incomplete Features

### 5.1 Enrollment Approval — **BROKEN**

**What exists**
- `status` Selection declares six values including `to_approve` and `withdrawn` (`models/enrollment/enrollment.py:111-124`)
- Buttons `action_confirm`, `action_complete`, `action_drop`, `action_reset_draft`, `action_withdraw`, `action_approve`, `action_reject` all exist (`enrollment.py:355-396`)

**What is wrong**
```python
# models/enrollment/enrollment.py:388-396
# Legacy method compatibility
def action_withdraw(self):
    return self.action_drop()

def action_approve(self):
    return self.action_confirm()

def action_reject(self):
    return self.action_drop()
```
`to_approve` and `withdrawn` are **never assigned anywhere** — grepping the whole module yields no writer. Therefore:
- The "approval" is really the same one-click confirm a student could perform
- There is no registrar gate, no approval queue, no rejection reason
- `withdrawn` is semantically different from `dropped` (withdraw usually follows add/drop deadline) but is unreachable

**What still needs implementation**
1. A `submitted` state and `action_submit()` that moves `draft → submitted`
2. `action_approve()` guarded by `group_school_registrar`/`group_school_admin`, moving `submitted → enrolled`
3. `action_reject(reason)` writing to a `reject_reason` field, moving `submitted → draft`
4. A "Pending Approval" kanban column and menu filter
5. Record rule limiting students to `create` + `read` only, no `write` on approved records

---

### 5.2 Student Attendance Workflow

**What exists** — `state` with `draft` / `recorded`, `action_save_attendance()` setting `recorded` (`models/attendance/attendance.py:48-53, 193-233`)

**What is missing** — submit → approve → reject, an approver trail, and a lock preventing post-approval edits. Note the **staff attendance model already implements exactly this** (`staff_attendance.py:234-262`) — the pattern exists and can be mirrored.

---

### 5.3 Room Availability

`models/academic/room_availability.py` (43 lines) exists with an ACL, but has **no views, no menu entry, and no action** — it is invisible to users and only queryable from the timetable engine.

---

### 5.4 Admission Stages

`admission.stage` (`models/admission/admission_stage.py`) with `data/admission/admission_stage_data.xml` and an ACL exists, but there are **no views and no menu**. `university.admission.application.state` uses a hard-coded Selection rather than pointing at stages, so the stage records are inert.

---

### 5.5 Admission Leads

`admission.lead` has model + form/list/kanban views + ACL, but there is **no `action_convert_to_application()`** and no `application_id` relationship — leads can never become applications through the UI.

---

### 5.6 Course Registration

- **No sequence record** for `university.course.registration` (grep of `data/` confirms only 9 sequences, none matching), so every registration is named `REG-YYYYMMDD` — non-unique per day (`course_registration.py:106`)
- Eligibility validation exists (`action_validate_eligibility`, line 109) but add/drop **deadline enforcement against `university.department.term.add_drop_end`** is not evident — needs runtime confirmation

---

### 5.7 Outstanding Fees

`payment_state`, `is_overdue` and `days_overdue` are computed and indexed (`models/finance/fee.py:82-103`), which is good, but there is **no aging report** (0–30 / 31–60 / 61–90 / 90+), no consolidated per-student statement, and no dunning sequence beyond a single reminder action.

---

### 5.8 Financial Reports

Only `reports/finance/payment_report.xml` (+ template) exists. Missing:
- Revenue by period (month / semester / academic year)
- Revenue by program / department
- Collection rate and outstanding totals
- Reconciliation report (fee ↔ payment ↔ (future) GL)

---

### 5.9 eLearning Course Management

The channel form gets three extra fields via `views/slide_channel_views.xml`, but:
- The constraint that validates section ↔ subject **crashes** (§6.1)
- There is **no manager-oriented analytical view** (no pivot/graph of channel engagement)

---

### 5.10 eLearning Academic Link

`class_section_id`, `subject_id` and `teacher_id` exist with onchanges, but the two `@api.constrains` methods are defective, and there is **no inverse workflow** (a section cannot push its enrolled students into the channel).

---

### 5.11 Record Rules

30+ rules exist but with defects:
- **Duplicate rules** for `university.assessment.result`: `security/security.xml:160-169` (`rule_teacher_ui_grades`) and `security/grading/record_rules.xml:133-141` (`rule_teacher_own_assessment_results`)
- **Missing HOD/Dean read rules** for `university.timetable.slot` — only admin and timetable-manager have `[(1,'=',1)]` (`security.xml:291-302`)
- **Orphan rule**: `rule_teacher_own_staff_attendance` (`security/attendance/record_rules.xml:75`) has no matching ACL row → unreachable

---

### 5.12 Multi-company

`company_id` exists on `university.fee`, `university.payment`, `university.assessment.result` and `university.transcript` only. Missing:
- Company record rules on any of them
- `check_company=True` on most relational fields
- `currency_id` is always `self.env.company.currency_id` (`fee.py:119-122`) — a record in another company would get the wrong currency

---

### 5.13 Enrollment → Book Purchase

`university.book.requirement` stores aggregate counts (`student_count`, `students_with_books`, `students_needing_books`), but there is **no per-student allocation record** — the system cannot answer "which student received which textbook".

---

### 5.14 Inventory Integration

Only reads `stock.quant` free quantity. There is no issue/return transaction to a student, and `custom/school_inventory` is an empty stub.

---

### 5.15 Course Evaluation

`university.course.evaluation` (225 lines) + views + limited ACL exist. Statically I cannot confirm that evaluation results feed any downstream report or inform instructor metrics → **NEEDS VERIFICATION**.

---

## 6. Part 5 — Integration Problems

### 6.1 Broken module wiring

| # | Issue | Evidence | Impact |
|---|---|---|---|
| 1 | `school_crm` has no manifest | only `__init__.py` present | Module cannot be installed |
| 2 | `school_inventory` has no manifest | only `__init__.py` present | Module cannot be installed |
| 3 | eLearning ACL never loaded | file is `school_eLearning/security/ir.model.access.csv.py`; manifest `data` lists no security file | New eLearning fields have no explicit ACL (falls back to inherited models) |
| 4 | eLearning ACL references a non-existent model | `model_school_subject` in `ir.model.access.csv.py` | Would fail on load if the extension were fixed |
| 5 | eLearning constraint crashes | `school_eLearning/models/slide_channel.py:43` — `.subject_id` read on `university.teacher` | Any `slide.channel` save with a class section raises `AttributeError` |
| 6 | Constraint writes during validation | `school_eLearning/models/slide_channel.py:33-37` assigns `self.teacher_id` inside `@api.constrains` | Side-effect during validation; may recurse or fail on multi-record writes |
| 7 | eLearning controller is a no-op | `controllers/main.py` → `class SchoolWebsiteSlides(WebsiteSlides): pass` | Inherits nothing; dead code |
| 8 | Dead duplicate purchase view file | `school_purchase/views/purchase_order_views.xml` re-declares `view_university_book_requirement_list/_form` and `action_university_book_requirement` already defined in `views/procurement/book_requirement_views.xml`; **not in manifest** | Adding it to the manifest would raise a duplicate-xmlid error |
| 9 | Purchase module deletes another module's data | `school_purchase/hooks.py` — deletes `ir_model_data` rows where `module='school_management'` and drops views/menus | Destructive cross-module side effect at install |
| 10 | Orphan wizard model with no UI | `subject.selection.wizard` (`wizard/academic/subject_selection_wizard.py`) + ACL row; `subject_selection_wizard.xml` is an empty `<odoo/>` and is not in the manifest | Dead model + dead ACL |
| 11 | Missing sequences (3) | `university.course.registration`, `university.service.request`, `university.student.change.request` — all fall back to date strings | Non-unique record names |
| 12 | `group_school_teacher` defined twice | `security/security.xml:45-49` and `:115-117`, each implying the other via `group_university_teacher` | Circular `implied_ids`; group semantics unpredictable |
| 13 | Public holiday import stub | `school_public_holiday/wizard/holiday/public_holiday_import_wizard_views.xml` is a 4-line empty stub loaded by the manifest | Harmless but misleading |

### 6.2 Data-flow disconnections

| Flow | Problem | Evidence |
|---|---|---|
| **Enrollment → Report Card** | Attendance component can pull records from *all* semesters when the subject has no resolvable section | `grading.py:479-483` |
| **Enrollment → Fee** | Fees are generated on **admission confirm** (`admission.py:532 → _generate_required_fee`) but **not** on ordinary enrollment creation → registration-time billing is manual | `models/enrollment/enrollment.py:398-420` |
| **Exam → Assessment Result** | Two parallel grading paths exist (`university.exam.score` vs `university.assessment.result`). Report cards read **only** `assessment.result` (`grading.py:446-451`); a separate sync from exam scores is required and is not statically evident | `models/grading/exam.py` vs `models/grading/grading.py` |
| **Student → GPA** | Three independent GPA implementations with different logic: `university.student.gpa`, `university.report.card.gpa`, `university.transcript.cumulative_gpa` | `student.py:175`, `grading.py:326/385`, `grading.py:698/715` |
| **eLearning → Academics** | No connection at all | §4.4–4.6 |

### 6.3 Duplication clusters

**Cluster 1 — Grading paths (DUPLICATED)**
`university.exam.score` (with late-penalty computation, `exam.py:815-836`) and `university.assessment.result` (with weighted-score computation, `grading.py:247-255`) both store a student score against a subject. Only the latter feeds report cards. Reconciliation logic is heuristic (matching category `code`/`name` substrings, `grading.py:496-545`).

**Cluster 2 — Calendar concepts (DUPLICATED-ish, justified)**
`university.semester` (institution-wide, 456 lines) and `university.department.term` (department-specific academic calendar, 357 lines). Both legitimate, but `department_term.py:95` builds `display_name` from `term.semester_id.name` without guarding empty semesters.

**Cluster 3 — Attendance models (DUPLICATED-ish, justified by audience)**
`university.attendance` (student, line-per-student) and `university.staff.attendance` (staff). Legitimate split, but with **divergent workflows** — staff has approval, students do not.

**Additional duplications**
- Duplicate `ir.rule` for `university.assessment.result` (see §5.11)
- Duplicate purchase view records (see §6.1 #8)
- Duplicate `group_school_teacher` (see §6.1 #12)

---

## 7. Part 6 — Security Audit

### 7.1 P0 — Confirmed vulnerabilities

#### S1. IDOR on dashboard JSON-RPC methods

**Location:** `models/dashboard/dashboard.py:1218-1230` and `1605-1618`
**Route:** `controllers/dashboard/dashboard.py:10` — `@http.route("/university/dashboard/data", type="jsonrpc", auth="user")`
**ACL:** `school.dashboard` has ACL rows for user/teacher/school-user/system (read-only) — so **any internal user** can invoke these methods.

```python
# models/dashboard/dashboard.py:1218
@api.model
def get_teacher_dashboard_data(self, year_id=False, semester_id=False, teacher_id=False):
    user = self.env.user
    teacher = False
    if teacher_id:
        try:
            teacher = self.env["university.teacher"].sudo().browse(int(teacher_id)).exists()
        except Exception:
            teacher = False
```

```python
# models/dashboard/dashboard.py:1605
@api.model
def get_student_dashboard_data(self, year_id=False, semester_id=False, student_id=False):
    user = self.env.user
    student = False
    if student_id:
        try:
            student = self.env["university.student"].sudo().browse(int(student_id)).exists()
        except Exception:
            student = False
    if not student:
        student = self.env["university.student"].sudo().search([("user_id", "=", user.id)], limit=1)
    if not student:
        student = self.env["university.student"].sudo().search([("status", "in", ("active", "graduated"))], order="id asc", limit=1)
    if not student:
        student = self.env["university.student"].sudo().search([], order="id asc", limit=1)
```

**Impact**
- Any authenticated user (any `base.group_user`) can pass `student_id=<other student>` and receive that student's grades, fee balances, attendance rate, risk level, schedule and report data.
- The same applies to `teacher_id` → teacher workload/private data.
- If the caller has **no** linked student profile, they silently receive the **first student in the database** — a data leak with no malicious intent required.
- `sudo()` bypasses all the record rules that the rest of the module carefully defines.

**Fix**
Resolve the record from `env.user` only; permit an explicit override **only** for `group_school_admin`, exactly as the portal controller does:

```python
# controllers/portal/student_portal.py:39-54  — the correct pattern already in this repo
if student_id and (user.has_group('base.group_system') or user.has_group('school_management.group_school_admin')):
    ...
student = Student.search([('user_id', '=', user.id)], limit=1)
```

Remove the "first student in DB" fallbacks entirely.

#### S2. Teacher write access beyond need on grades and attendance

**Location:** `security/security.xml:130-169`

```xml
<record id="rule_teacher_ui_grades" model="ir.rule">
  <field name="domain_force">[('section_id.teacher_id.user_id', '=', user.id)]</field>
  <field name="perm_read" eval="True"/>
  <field name="perm_write" eval="True"/>
  <field name="perm_create" eval="True"/>
</record>
```

Because `group_school_hod` implies `group_school_teacher` and `group_school_dean` implies `group_school_hod` (`security.xml:64-74`), every HOD and Dean inherits this permissive section-scoped write rule **in addition to** their own department/faculty-scoped rules. Python-level guards (`_allowed_edit`) protect the OWL sheet path but are bypassed by direct `write()` RPC calls on `university.assessment.result` / `university.attendance`.

**Additionally:** `university.assessment.result.write()` (`grading.py:285-289`) only blocks **closed academic years** — it does **not** protect `published` results from teacher modification.

**Fix**
- Split the teacher rule into read-only, and add a separate write rule gated on `state != 'published'`
- Add a Python guard in `UniversityAssessmentResult.write()` rejecting writes when `state == 'published'` unless the user holds registrar/admin
- Add explicit HOD/Dean rules rather than relying on group implication for write

#### S3. Rule OR-semantics void the restrictive rule

Two rules target the same model + group:
- `rule_teacher_own_assessment_results` — read-only (`security/grading/record_rules.xml:133-141`)
- `rule_teacher_ui_grades` — read + write + create (`security/security.xml:160-169`)

Odoo **ORs** record rules within the same group, so the narrower rule has no effect. This is a silent privilege escalation and a maintenance trap: someone reading `record_rules.xml` will believe grades are read-only for teachers.

### 7.2 P1 — Access-control gaps

| # | Gap | Evidence | Consequence |
|---|---|---|---|
| 1 | Teacher has a record rule but **no ACL** on `university.staff.attendance` | ACL file grants admin/dean/hod only; rule at `security/attendance/record_rules.xml:75` | Teacher gets `AccessError`; rule unreachable. Also **no registrar row at all** |
| 2 | No HOD/Dean read scope on `university.timetable.slot` | Only admin + timetable-manager `[(1,'=',1)]` (`security.xml:291-302`) | Department heads cannot view their own department's timetable unless also timetable manager |
| 3 | `base.group_user` has no access to `university.course.evaluation`, `university.staff.attendance`, `university.student.change.request` | ACL group sets exclude `base.group_user`/`base.group_system` | Non-university internal users get `AccessError` — verify this is intentional |
| 4 | `signature` Binary field without `attachment=True` | `models/core/document_signature.py:29` | Signature blobs stored in-DB, duplicated on record copy |
| 5 | Portal transcript POST should ignore client-supplied `student_id` | `controllers/portal/student_portal.py:238-256` | Currently appears to derive server-side — **must be confirmed and asserted explicitly** |
| 6 | Duplicate `to_approve` / `withdrawn` states with no ACL distinction | `enrollment.py:111-124` | Students can call `action_confirm()` directly; no approval separation of duties |

### 7.3 P2 — Hardening

| # | Issue | Evidence |
|---|---|---|
| 1 | Public `/admission/apply` uses `sudo()` and has **no rate limit or CAPTCHA** | `school_website/controllers/admission/admission.py:33-82` → spam / DB growth DoS |
| 2 | LLM API key stored in plain `Char` with no group restriction | `school_website/models/chatbot/chatbot_script.py:31` |
| 3 | ~110 DB-mutating scripts shipped inside the installable module | `school_management/scratch/` (`apply_updates.py`, `patch_*.py`, `upgrade_module.py`, `seed/`, `scripts/`) |
| 4 | No multi-company record rules on financial models | `security/finance/record_rules.xml` has no `company_id` domain |
| 5 | Circular group implication | `security.xml:45-49` ↔ `:115-117` for `group_school_teacher` |
| 6 | Purchase module deletes `school_management` records at install | `school_purchase/hooks.py` |

### 7.4 Positive security findings

- **All 63 concrete models have ACL rows** (`319` rows across 10 CSV files)
- **Record rules** implement genuine row-level security for students (own records), teachers (assigned sections), HOD (department), Dean (faculty) and registrar (all)
- **Portal** correctly resolves the student from `env.user` (`controllers/portal/student_portal.py:39-54`) — the correct pattern that the dashboard should copy
- **Academic year locking** is enforced uniformly on create/write/unlink for grades, report cards, holidays, enrollments and assessment results
- **Download mixin** checks state + group before producing PDF/XLSX and logs the download (`models/core/document_download_mixin.py:15-26`)
- **Public website controllers** consistently use `sudo()` with explicit, safe domains on read-only public data

---

## 8. Part 7 — Recommended Architecture

### 8.1 Target shape (preserve the current split)

```
school_management  — core academic / people / finance / attendance / grading
├── academic/   faculty → department → program → curriculum → semester → subject → section → timetable
├── people/     student, teacher  (both linked to res.users, rule-scoped)
├── enrollment/ admission/ advising/
├── attendance/ grading/ finance/
└── core/       capability, settings, document (signature + download mixin)

extensions — each one clear seam, no core edits:
  school_eLearning       → website_slides bridge (enrollment / progress / completion)
  school_purchase        → purchase_stock bridge (book requirement → RFQ)
  school_public_holiday  → holiday calendar + schedule conflict validation
  school_website         → public portal + admission intake + chatbot
  school_accounting (NEW)→ thin adapter: fee/payment → account.move
```

### 8.2 Recommendations

1. **Introduce one approval mixin.**
   A shared `university.approval.mixin` providing `draft → submitted → approved / rejected` with `approver_id`, `reject_reason`, `approved_on`. Apply to: attendance sessions, enrollment, report cards, service requests, transcripts. This replaces five bespoke state machines with one tested implementation.

2. **Make grading single-sourced.**
   Choose `university.exam` → `university.exam.score` → **auto-create/update** `university.assessment.result`. Delete the heuristic string matching in `grading.py:496-545` and `assessment.category._compute_category_metrics` (`grading.py:132-137`).

3. **Extract a GPA service.**
   One abstract model `university.grade.service` with `compute_gpa(student, year, semester)`, `compute_cumulative(student)`, `resolve_grade(score)`. Call it from student, report card and transcript so the three implementations cannot drift.

4. **Introduce a money layer, don't reinvent accounting.**
   New `school_accounting` module that **inherits** `university.fee` / `university.payment` and posts `account.move` on `action_post()` and reverses on `action_cancel()`. This *uses* standard Odoo functionality rather than duplicating it — exactly what AGENTS.md §2.1 requires.

5. **Consolidate security.**
   One rule file per model. Delete overlapping rules from `security/security.xml`. Replace every `sudo().browse(user_supplied_id)` with a single helper `_resolve_scope_record(model, user, requested_id)` that enforces ownership unless admin.

6. **Add per-student textbook allocation.**
   `university.book.allocation` linking `university.enrollment`, `university.subject.book`, `stock.move`. Makes the procurement loop close.

7. **Remove development artefacts from the shippable module.**
   Move `scratch/`, `scripts/`, `seed/` and `document/` out of `school_management` (or exclude via `__manifest__` packaging / `.gitignore`).

8. **Normalise sequences.**
   Create the 3 missing sequences and add `sql_constraints` on the generated name fields so date-based fallbacks can never collide.

---

## 9. Part 8 — Implementation Roadmap

### P0 — Critical errors and security problems

| # | Task | Affected files | Dependencies |
|---|---|---|---|
| **P0-1** | Close dashboard IDOR: derive student/teacher from `env.user`; allow override only for `group_school_admin` | `models/dashboard/dashboard.py:1218-1230, 1605-1618` | — |
| **P0-2** | Remove "first student/teacher in DB" fallbacks | same file | P0-1 |
| **P0-3** | Fix eLearning constraint crash (`teacher.subject_ids`; no writes inside `@api.constrains`) | `school_eLearning/models/slide_channel.py:33-46` | — |
| **P0-4** | Rename `security/ir.model.access.csv.py` → `.csv`; remove `model_school_subject` row; add to manifest `data` | `school_eLearning/security/`, `school_eLearning/__manifest__.py` | P0-3 |
| **P0-5** | Add missing teacher ACL row for `university.staff.attendance`; add registrar row | `school_management/security/attendance/ir.model.access.csv` | — |
| **P0-6** | Remove duplicate `ir.rule` for assessment results; resolve the double `group_school_teacher` definition and circular implication | `security/security.xml:45-49,115-117,160-169`; `security/grading/record_rules.xml:133-141` | — |
| **P0-7** | Add Python guard preventing writes to `published` assessment results | `models/grading/grading.py:285-289` | P0-6 |
| **P0-8** | Decide the fate of the two empty modules and the dead purchase view file (complete or delete) | `school_crm/`, `school_inventory/`, `school_purchase/views/purchase_order_views.xml` | — |

### P1 — Core university business processes

| # | Task | Affected files | Dependencies |
|---|---|---|---|
| **P1-1** | Real enrollment approval: `draft → submitted → approved/rejected`, registrar gate, reject reason, kanban column; retire or implement `to_approve` / `withdrawn` | `models/enrollment/enrollment.py:111-124, 388-396`; `views/enrollment/enrollment_views.xml`; `security/enrollment/record_rules.xml` | P0-6 |
| **P1-2** | Student attendance approval workflow, mirroring staff attendance | `models/attendance/attendance.py:48-53, 193-233`; `views/attendance/attendance_sheet_views.xml`; OWL sheet JS | P1-1 pattern |
| **P1-3** | Unify grading: exam score → assessment result auto-sync | `models/grading/exam.py`, `models/grading/grading.py` | — |
| **P1-4** | Fix report-card attendance scoping (add year+semester domain); add grade-scale overlap constraint | `models/grading/grading.py:46-54, 479-483` | — |
| **P1-5** | Add the 3 missing `ir.sequence` records + uniqueness constraints | `data/finance/fee_sequence.xml` or new `data/core/sequences.xml` | — |
| **P1-6** | Accounting adapter: post `account.move` on payment, reverse on cancel, backfill migration | new `custom/school_accounting/` | P1-5 |

### P2 — Missing functionality

| # | Task | Affected files | Dependencies |
|---|---|---|---|
| **P2-1** | eLearning bridge: auto-enroll from `university.enrollment` into `slide.channel.member`; progress → completion → credits | `school_eLearning/models/`, new `slide_channel_member.py`, `enrollment.py` | P0-3 |
| **P2-2** | Student document vault (model, views, ACL, portal tab) | new `models/people/student_document.py` + views + ACL | — |
| **P2-3** | Discipline management (case + sanction models, workflow, dashboard tile) | new `models/discipline/` + views + ACL | — |
| **P2-4** | Admission stage UI + lead → application conversion action | `models/admission/admission_stage.py`, `views/admission/*` | — |
| **P2-5** | Outstanding-fee aging report + revenue-by-program report | `reports/finance/` | P1-6 |
| **P2-6** | Per-student textbook allocation / issue records | `school_purchase/models/`, `school_inventory` (implement or drop) | — |

### P3 — UI/UX improvements and optimisation

| # | Task | Affected files | Dependencies |
|---|---|---|---|
| **P3-1** | Room availability views + menu + timetable conflict surfacing | `views/academic/room_availability_views.xml` | — |
| **P3-2** | Resolve orphan `subject.selection.wizard` (build a real view, or delete the model + ACL row) | `wizard/academic/`, `security/academic/ir.model.access.csv` | — |
| **P3-3** | HOD/Dean read scope on timetable slots and grades | `security/security.xml` | P0-6 |
| **P3-4** | Multi-company record rules + `check_company` audit + currency per company | `security/finance/record_rules.xml`, model field definitions | P0-6 |
| **P3-5** | Move `scratch/`, `scripts/`, `seed/`, `document/` out of the shippable module | module root | — |
| **P3-6** | Add CAPTCHA / rate limiting to the public admission endpoint | `school_website/controllers/admission/admission.py` | — |
| **P3-7** | Restrict chatbot `ai_api_key` field by group | `school_website/models/chatbot/chatbot_script.py:31` | — |

### Suggested sequence

```
Week 1  : P0-1 … P0-8            (security + crashes; nothing else should ship before these)
Week 2-3: P1-1 … P1-5            (core workflow correctness)
Week 3-4: P1-6                   (accounting, needs account chart of accounts configured)
Week 4-6: P2-1 … P2-6            (missing features)
Week 6+ : P3-1 … P3-7            (polish)
```

---

## 10. Verification Caveats

1. **This audit is static.** No Odoo instance was booted and no database was queried. Conclusions are drawn from source inspection and cross-referencing.

2. **`NEEDS VERIFICATION` items** — runtime behaviour not confirmed:
   - `university.course.evaluation` — whether results feed any downstream report
   - Exam → assessment-result synchronisation path
   - JSON-RPC role routing inside the dashboard shell JS
   - Add/drop deadline enforcement in course registration

3. **Field-resolution scope.** View field checks covered outer view archs. Fields referenced inside nested one2many / many2many sub-views were **not** individually validated.

4. **Recommended runtime validation.** Running the existing test suite would resolve most open questions:
   ```bash
   odoo-bin --test-tags /school_management --stop-after-init
   odoo-bin --test-tags /school_public_holiday --stop-after-init
   odoo-bin --test-tags /school_purchase --stop-after-init
   ```
   264 test methods are already wired in `tests/__init__.py`; adding coverage for the dashboard RPCs and eLearning constraints would close the two largest blind spots.

5. **No repository files were created, modified or deleted during this audit.** All analysis scripts were written outside the repository (`C:\Users\Rith2\.rayu\tmp\`).

---

## 11. Appendix A — Model Inventory

**63 concrete models + 3 inherited/abstract**

```
Academic
  university.faculty              university.department            university.department.term
  university.program              university.academic.year         university.semester
  university.subject              university.semester.subject      university.curriculum
  university.curriculum.line      university.class.section         university.classroom
  university.room.availability    university.class.schedule.line   university.academic.assignment
  university.lesson.plan          university.timeslot              university.timetable.slot
  university.timetable.conflict   university.subject.book          time.config

Admission / Enrollment / Advising
  university.admission.application   admission.stage    admission.lead
  university.enrollment              university.student.advising.note
  university.student.followup        university.student.change.request

People
  university.student     university.teacher     res.users (inherit)

Attendance
  university.attendance.session   university.attendance   university.staff.attendance
  university.holiday              university.attendance.take.wizard
  university.attendance.take.wizard.line   university.attendance.print.wizard

Grading
  university.grade.scale          university.grade.scale.line
  university.assessment.category  university.assessment.result
  university.report.card          university.report.card.line
  university.transcript           university.transcript.line
  university.exam                 university.exam.score
  university.transcript.request

Finance
  university.fee                  university.fee.line
  university.fee.structure        university.fee.structure.line
  university.payment              university.fee.payment.wizard

Assignment
  university.assignment           university.assignment.submission

Core / Dashboard
  university.capability           university.notice.board        school.dashboard
  university.service.hour         university.service.request
  university.document.signature   university.document.download.mixin (abstract)

Wizards
  university.student.enrollment.wizard   university.bulk.enrollment.wizard
  university.bulk.enrollment.wizard.line university.populate.class.wizard
  university.teacher.account.wizard      university.timetable.generation.wizard
  university.year.rollover.wizard        university.transcript.request.override.wizard
  university.transcript.request.reject.wizard   subject.selection.wizard (orphan)

Inherited
  res.config.settings     ir.ui.menu     product.template     resource.resource
```

**Extension modules**

```
school_eLearning      : slide.channel (inherit), university.subject (inherit),
                        university.class.section (inherit)
school_purchase       : purchase.order (inherit), university.class.section (inherit),
                        university.subject (inherit), university.enrollment (inherit),
                        university.book.requirement (new)
school_public_holiday : public.holiday (new), holiday.import.log (new),
                        university.class.section / timetable.slot / attendance /
                        staff.attendance / exam / notice.board / dashboard (inherit)
school_website        : chatbot.script (inherit), chatbot.script.step (inherit),
                        discuss.channel (inherit), res.config.settings (inherit),
                        website / website.menu / website.visitor (inherit)
```

---

## 12. Appendix B — Module Inventory

| Module | Manifest version | Depends | Installable | State |
|---|---|---|---|---|
| `school_management` | `19.0.2.3.0` | auth_signup, base, mail, portal, product, web, spreadsheet_dashboard, resource | ✅ | Core, 425 files |
| `school_eLearning` | `19.0.1.0.0` | website_slides, school_management | ✅ | Bridge, defects in §6.1 |
| `school_purchase` | `19.0.1.2.1` | purchase_stock, school_management | ✅ | Bridge, `pre_init_hook` cleans `school_management` data |
| `school_public_holiday` | `1.0.0` | base, resource, mail, school_management | ✅ | Working |
| `school_website` | `19.0.1.0.0` | website, school_management, im_livechat | ✅ | Working |
| `school_crm` | — | — | ❌ **no manifest** | **Empty stub** |
| `school_inventory` | — | — | ❌ **no manifest** | **Empty stub** |

---

## Sign-off

**Audit complete.** No code has been modified. No feature has been implemented.

**Awaiting your review and approval before any implementation begins.**

Recommended starting point, by risk:
1. **P0-1 / P0-2** — close the dashboard IDOR (student/teacher data leak)
2. **P0-3 / P0-4** — fix the eLearning crash and dead security file
3. **P0-5 / P0-6 / P0-7** — repair ACL and record-rule gaps
4. **P1-1** — implement a genuine enrollment approval workflow
