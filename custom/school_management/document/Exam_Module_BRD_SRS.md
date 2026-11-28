# Exam Management Integration — University Project (Odoo 19)
### Business Requirements Document (BRD) & System Requirements Specification (SRS)

---

## PART 1 — BUSINESS REQUIREMENTS DOCUMENT (BRD)

### 1.1 Purpose
The University Operations system currently manages students, enrollment, class sections, teachers, and grading, but has no structured way to run **Quizzes, Midterm Exams, and Final Exams**. This document defines the business need and functional expectations for adding an Exam module that plugs into the existing Grading, Enrollment, and Attendance features.

### 1.2 Background / Problem Statement
- Teachers currently have no standard place to record quiz/midterm/final scores; grading is likely done ad hoc or outside Odoo.
- There is no weighting rule linking Quiz + Midterm + Final into a final course grade.
- Admin/Dean/Head of Faculty have no way to see exam completion status per section, or to audit scores.
- Students have no visibility into their own exam results.

### 1.3 Business Objectives
| # | Objective |
|---|---|
| B1 | Give teachers a fast way to create exams/quizzes and enter scores per class section |
| B2 | Standardize how Quiz, Midterm, and Final scores roll up into a final grade |
| B3 | Give Admin/Dean/Head of Faculty oversight and reporting across faculties |
| B4 | Give students (and optionally parents) visibility into their own results |
| B5 | Keep exam records tied to the correct enrollment, section, semester, and academic year |
| B6 | Prevent duplicate/conflicting score entries and enforce data integrity |

### 1.4 Stakeholders
| Stakeholder | Interest |
|---|---|
| Admin / University Management | Full oversight, configuration, reporting, corrections |
| Dean | Faculty-level visibility into exam performance |
| Head of Faculty | Department-level exam oversight and approvals |
| Teacher | Creates exams, enters/edits scores for their own sections |
| Student | Views own exam schedule and results (read-only) |
| Registrar (if applicable) | Uses final grades for transcripts/certification |

### 1.5 Scope
**In scope:**
- Three exam types: **Quiz**, **Midterm Exam**, **Final Exam** (extensible list)
- Exam definition (subject, section, semester, academic year, max score, weight, date)
- Score entry per student per exam
- Automatic/weighted final grade computation feeding into the existing Grading module
- Role-based access (Admin, Dean, Head of Faculty, Teacher, Student)
- Basic reporting (class average, pass/fail rate, per-student transcript)

**Out of scope (for this phase):**
- Online exam-taking / auto-graded question banks (multiple choice engine)
- Anti-cheating or timed-exam proctoring
- Payment/fee linkage to exam retake fees
- Mobile app changes (student portal is web-based only)

### 1.6 Business Rules
1. An exam (Quiz/Midterm/Final) must belong to exactly one **Subject + Class Section + Semester + Academic Year**.
2. Only students **enrolled** (state = Enrolled) in that section/semester may receive a score for that exam.
3. A student can have only **one score per exam** (no duplicates).
4. Each exam type has a **default weight** toward the final grade (example: Quiz 20%, Midterm 30%, Final 50%), configurable per subject.
5. Final grade = weighted sum of Quiz + Midterm + Final scores (normalized to 100), computed automatically once all required scores are entered.
6. A teacher may only create/edit exams and scores for sections **they teach**.
7. Admin can create/edit/delete any exam or score, for audit/correction purposes.
8. Dean and Head of Faculty have **read-only** access scoped to their own faculty (matches existing attendance/enrollment security model).
9. Students see only **their own** results, and only after a teacher marks the exam as **Published** (scores must not be visible while still in draft/grading).
10. An exam cannot be deleted once scores exist, unless the user is Admin.
11. Each exam has a **start time and end/deadline time**. A student's attempt or score submitted after `end_time` is flagged as **late**; whether it is accepted at all, or accepted with a penalty, is controlled by `late_submission_allowed` and `late_penalty_percent` on the exam.
12. A quiz/exam cannot move to `open` state before its `start_time`, and the system should auto-transition it to `closed` once `end_time` passes (scheduled action or computed state), so teachers don't have to close it manually.
13. Scores can only be entered while the exam is `open`, `closed`, or `grading` — not while still `draft`/`scheduled` (nothing to grade yet) and not once `published` (locked, edits require Admin override).
14. A **plain exam (quiz)** is auto-created by a scheduled action the moment a class session's `start_time` is reached, for any subject/section flagged as requiring a per-session quiz; the teacher only enters scores, nothing else. Midterm/Final exams remain one-off, created ahead of the midterm/final week (manually or via a separate scheduled event), not per class session.
15. The class average (`average_score`) must always reflect only the scores entered **so far** (not require every student to be graded first), so a teacher can track progress mid-grading.
16. The quiz auto-creation cron (rule 14) must only create exams for timetable slots whose **semester is currently active** (`today` falls within `semester.start_date`–`semester.end_date`). A timetable slot belonging to a past or future semester must never spawn an exam.
17. Midterm and Final exam dates should fall within the owning semester's `start_date`–`end_date` range; the system should warn (not necessarily block) if a Final Exam is scheduled before the semester's midpoint, or a Midterm after it.

### 1.7 Assumptions & Constraints
- Existing models `university.student`, `university.enrollment`, `university.class.section`, `university.subject` (or `semester_subject`), `university.staff` (teacher), `university.grading` already exist and will be reused, not duplicated.
- Existing security groups (Admin/manager, Dean, Head of Faculty, Teacher, Student) will be reused — no new groups unless necessary.
- The system runs on Odoo 19 with the module `school_management`.
- No integration with external LMS/exam platforms in this phase.

### 1.8 Success Criteria
- A teacher can create a Midterm exam for their section and enter scores for all enrolled students in under 5 minutes.
- Final grade recalculates automatically when any component score changes.
- Admin can view all exam records across every faculty; a Dean/Head of Faculty sees only their own faculty's data; a student sees only their own results.
- No duplicate exam scores can be created for the same student/exam.

---

## PART 2 — SYSTEM REQUIREMENTS SPECIFICATION (SRS)

### 2.1a Semester Date Range (prerequisite for auto-creation)

For the timetable-triggered auto-creation (2.1.1) to know when it's allowed to run, the **Semester** master data needs a defined active period:

**`university.semester`** (existing model — add if missing)
| Field | Type | Notes |
|---|---|---|
| start_date | Date | first day of the semester |
| end_date | Date | last day of the semester |
| is_active | Boolean or computed | True when `start_date ≤ today ≤ end_date` |

Business impact:
- The quiz auto-creation cron only fires for timetable slots whose section/semester is **currently active** (`start_date ≤ today ≤ end_date`). No quizzes get created before the semester starts or after it ends, even if a stray timetable slot exists.
- Midterm exams are expected roughly mid-semester and Final exams near `end_date` — the exam creation screen can suggest/validate a sensible date range (e.g. warn if a "Final Exam" is dated before the semester's midpoint).
- Enrollment, attendance, and exam records for a semester can now be filtered/reported against a real calendar window instead of just a label ("Semester 1"), which also fixes the inconsistent naming issue noted earlier ("S1" vs "Semester 1" vs "Full Semester").

### 2.1 Proposed Data Model

**`university.exam`** (defines one exam instance)
| Field | Type | Notes |
|---|---|---|
| name | Char | e.g. "Midterm – Database Systems" |
| exam_type | Selection | `quiz`, `midterm`, `final` |
| subject_id | Many2one → subject/semester_subject | required |
| section_id | Many2one → university.class.section | required |
| timetable_slot_id | Many2one → university.timetable | optional; the class session that triggered auto-creation (traceability) |
| auto_created | Boolean | True if generated automatically when the class session started, False if created manually |
| academic_year_id | Many2one | required |
| semester_id | Many2one | required |
| teacher_id | Many2one → university.staff | default: current user's staff record |
| exam_date | Date | calendar date of the exam |
| start_time | Datetime | when the exam/quiz opens |
| end_time | Datetime | when the exam/quiz closes (deadline) |
| duration_minutes | Integer | computed or manual; how long a student has once started |
| late_submission_allowed | Boolean | default False |
| late_penalty_percent | Float | applied if a late submission is allowed, e.g. -10% |
| max_score | Float | default 100 |
| weight_percent | Float | default from subject config, editable |
| state | Selection | `draft`, `scheduled`, `open`, `closed`, `grading`, `published`, `cancelled` |
| average_score | Float | computed: average of all entered `university.exam.score.score` for this exam (auto-updates as scores are entered) |
| scored_count | Integer | computed: how many students have a score entered so far |
| student_count | Integer | computed: total eligible students (from enrollment), for a "12/30 graded" progress indicator |
| _rec_name | computed | "Subject – Exam Type – Section – Date" |

> `start_time`/`end_time` matter most for **Quiz** (often timed, single sitting) and can be optional for **Midterm/Final**, which may just need a date + venue/session rather than a strict online window. Keep both fields on the same model so the UI can hide/show them per `exam_type`.

#### 2.1.1 Simplified "Plain Exam" flow — auto-created when class starts

Rather than the teacher manually opening a "New Exam" form, the plain exam is **generated automatically** the moment a class session begins, using the existing **Timetable** model as the trigger:

1. Every class section already has scheduled sessions in `university.timetable` (day, start time, end time, subject, teacher).
2. A **scheduled action (cron)**, running every few minutes, checks for timetable slots whose `start_time` has just been reached for sections that are flagged as "requires plain exam" (e.g. subjects that run a quiz/exam every session, configurable per subject or per section).
3. For each matching slot, the system auto-creates a `university.exam` record with:
   - `subject_id`, `section_id`, `teacher_id`, `academic_year_id`, `semester_id` — pulled from the timetable slot
   - `timetable_slot_id` set to that session (for traceability)
   - `auto_created = True`
   - `exam_type` defaulting to `quiz` (configurable — a section could instead auto-create a "midterm" on its designated midterm week)
   - `exam_date` = today, `state = open`
   - `max_score` = the subject's configured default (e.g. 100), editable by the teacher
4. The teacher does **not** need to fill in any setup fields — the exam is already waiting for them when class starts. They only need to **enter each student's score** (the "total score" they're marking out of `max_score`).
5. `average_score` recomputes live as scores are entered, exactly as described above (e.g. "Class average: 78.4/100, 18/25 graded").
6. Teacher marks it **Published** when done. If a class session passes with no scores entered at all, the exam stays `open`/`draft` and shows up in a "Pending grading" list for the teacher (and for Head of Faculty, as a follow-up item).
7. A teacher can still create an exam **manually** for a one-off case (e.g. a surprise quiz not tied to a timetable slot) — auto-creation is the default path, not the only path. `auto_created = False` distinguishes manually created exams from timetable-triggered ones.

This auto-creation should be **configurable per subject/section** — not every class needs a quiz every session (a lecture-only session shouldn't spawn an empty exam record). A boolean like `subject_id.auto_quiz_per_session` (or similar, on the subject/section master data) controls whether the cron creates an exam for that session at all.

Midterm and Final exams are one-off events tied to a specific date on the academic calendar (not "every class session"), so they are **not** auto-created by this per-session cron — they follow the manual/scheduled path from section 2.1, created once for the whole section ahead of the midterm/final week.

**`university.exam.score`** (one row per student per exam)
| Field | Type | Notes |
|---|---|---|
| exam_id | Many2one → university.exam | required |
| student_id | Many2one → university.student | required, domain limited to students enrolled in exam's section |
| enrollment_id | Many2one → university.enrollment | optional link for traceability |
| score | Float | required, 0 ≤ score ≤ exam.max_score |
| remark | Char | optional (absent, excused, etc.) |
| is_absent | Boolean | if true, score forced to 0 or null per business rule |
| submitted_at | Datetime | when the student's attempt/answer was recorded (for online quizzes) |
| is_late | Boolean | computed: `submitted_at > exam_id.end_time` |

- **Unique constraint:** (exam_id, student_id)
- **Computed on `university.grading` (or wherever final grade lives):** weighted average pulling from published `university.exam.score` records grouped by student + subject + semester.

### 2.2 Functional Requirements

| ID | Requirement |
|---|---|
| FR1 | System shall allow Teacher/Admin to create an Exam record scoped to subject + section + semester + academic year |
| FR2 | System shall auto-populate the list of eligible students from **current enrollments** of the exam's section (not a static list) |
| FR3 | System shall provide a bulk score-entry screen: one row per student, with a score input and an "Absent" toggle, similar in spirit to the bulk attendance sheet |
| FR4 | System shall block scores above `max_score` or below 0, with a clear validation error |
| FR5 | System shall prevent duplicate scores for the same student/exam (unique constraint + UI-level upsert) |
| FR6 | System shall compute final grade automatically as: `(quiz_score/quiz_max × quiz_weight) + (midterm_score/midterm_max × midterm_weight) + (final_score/final_max × final_weight)`, only when the exam's `state = published` |
| FR7 | System shall keep exam scores hidden from students until the exam is marked **Published** |
| FR7a | System shall enforce `start_time`/`end_time` on each exam: state auto-transitions to `open` at start and `closed` at end (via a scheduled action or computed state), and shall flag any score/attempt recorded after `end_time` as late |
| FR7b | System shall apply `late_penalty_percent` automatically to a late score when `late_submission_allowed = True`, and shall reject/flag the attempt when late submission is not allowed |
| FR7c | System shall run a scheduled action (cron) that auto-creates a `university.exam` (quiz) the moment a class session's `start_time` is reached, for any section/subject flagged as requiring a per-session quiz, pre-filling subject/section/teacher/semester from the timetable slot and setting `auto_created = True` |
| FR7c-2 | System shall allow a teacher to still create an exam manually (`auto_created = False`) for one-off cases not tied to a timetable slot |
| FR7e | System shall restrict the quiz auto-creation cron to timetable slots whose semester is currently active (`start_date ≤ today ≤ end_date`); no exams shall be created outside that window |
| FR7f | System shall warn (non-blocking) if a Midterm or Final exam's `exam_date` falls outside a sensible position within the semester's date range (e.g. Final before the semester midpoint) |
| FR7d | System shall compute and display `average_score` live, updating as each score is entered, without requiring all students to be graded first |
| FR8 | Teacher shall only see/edit exams and scores for sections they teach |
| FR9 | Admin shall have full CRUD on all exams and scores across all faculties |
| FR10 | Dean and Head of Faculty shall have read-only access scoped to their own faculty |
| FR11 | Student shall have read-only access to their own **published** exam scores only |
| FR12 | System shall provide a class-level report: average score, highest/lowest, pass/fail count per exam |
| FR13 | System shall provide a per-student transcript view combining Quiz/Midterm/Final/Final Grade per subject/semester |
| FR14 | System shall log exam state changes (draft → scheduled → grading → published) in the chatter for audit |
| FR15 | System shall prevent deleting an exam that already has scores, unless the user is Admin |

### 2.3 Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | Bulk score entry for a section of ~50 students should load and save in under 2 seconds |
| Usability | Score entry screen should mirror the existing bulk attendance sheet UX (same visual pattern, so teachers reuse muscle memory) |
| Security | All access enforced via Odoo `ir.model.access.csv` + `ir.rule`, consistent with existing attendance/enrollment security model |
| Data integrity | Unique constraints via `models.Constraint`; validation via `@api.constrains` |
| Auditability | Full chatter/mail thread on `university.exam` for state changes and corrections |
| Compatibility | Odoo 19 syntax only (`<list>`, `invisible="expr"`, `models.Constraint`) |
| Maintainability | Reuse existing subject, section, enrollment, and staff models — no duplicate master data |

### 2.4 Integration Points with Existing Modules

| Existing Module | Integration |
|---|---|
| `university.enrollment` | Source of truth for which students are eligible for an exam's section/semester |
| `university.class.section` | Determines which teacher can manage which exam (via `teacher_ids`) |
| `university.grading` | Receives computed final grade per student/subject/semester |
| `university.attendance` | No direct dependency, but UI pattern (bulk sheet) should be reused for consistency |
| Security groups | Reuse Admin, Dean, Head of Faculty, Teacher, Student groups already defined |

### 2.5 Security Model (Access Matrix)

| Role | Create Exam | Edit Exam | Delete Exam | Enter Scores | View Scores |
|---|---|---|---|---|---|
| Admin | Yes | Yes | Yes | Yes | All |
| Head of Faculty | Yes (own faculty) | Yes (own faculty) | No | Yes (own faculty) | Own faculty |
| Dean | No | No | No | No | Own faculty (read-only) |
| Teacher | Yes (own sections) | Yes (own sections) | No | Yes (own sections) | Own sections |
| Student | No | No | No | No | Own published scores only |

### 2.6 Reporting Requirements
- Pivot/graph view: average score by exam type, by section, by subject.
- List view: exams not yet published, grouped by teacher — for Head of Faculty to chase overdue grading.
- Student-facing "My Results" view: read-only list of published exams with scores and final grade.

### 2.7 Open Questions (to confirm before build)
1. Should the weight (Quiz/Midterm/Final %) be configured **per subject** or be a **global default**?
2. What happens to the final grade if a student is marked absent for one component — zero, excluded from weighting, or requires a retake workflow?
3. Should Dean be allowed to edit scores for corrections, or strictly view-only (current assumption: view-only)?
4. Is a "retake exam" scenario needed in this phase, or deferred?
5. Do Midterm/Final exams need a strict `start_time`/`end_time` window (like an online quiz), or just an `exam_date` + session/venue, since they're often on-paper/in-person? *(Leaning: just a date within the semester range — see 2.1a — unless a specific need for timed midterms/finals comes up.)*
6. Should the `open` → `closed` state transition run automatically via a scheduled action (cron), or is it acceptable for a teacher to close it manually?
7. Where should the "requires per-session quiz" flag live — on the **Subject** (applies to every section teaching it) or on the **Class Section** (so one teacher's section auto-quizzes but another section of the same subject doesn't)?
8. If a class session is cancelled/rescheduled in the Timetable, should its auto-created exam be cancelled too, or left for the teacher to clean up manually?
9. Does `university.semester` already have `start_date`/`end_date` in the current codebase, or does this need to be added as new fields + a data migration for existing semester records (e.g. "Semester 1", "S1")?

---

## Suggested Build Order
1. `university.exam` and `university.exam.score` models + constraints
2. Security groups/rules (reuse existing) + access rights
3. Bulk score-entry OWL screen (reuse attendance-sheet pattern)
4. Final grade computation → link into `university.grading`
5. Reporting views (pivot, class report, student "My Results")
6. Publish/state workflow + chatter audit trail
