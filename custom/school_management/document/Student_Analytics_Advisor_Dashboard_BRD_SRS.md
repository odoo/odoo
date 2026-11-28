# Student Analytics & Advisor Dashboard — University Project (Odoo 19)
### Business Requirements Document (BRD) & System Requirements Specification (SRS)

**Source capability record:** Category: System · Status: Planned · Phase 3 · Target version: 19.0.2.0 · Description: *"Academic progress analytics, advisor views and retention insight."*

---

## PART 1 — BUSINESS REQUIREMENTS DOCUMENT (BRD)

### 1.1 Purpose
Give academic advisors, Heads of Department, Deans, and Admin a single dashboard that surfaces each student's academic progress, flags students at risk of falling behind or dropping out, and gives advisors a working view of only the students assigned to them — pulling from data that already exists across Enrollment, Attendance, Exam/Grading, and Fee modules, rather than requiring anyone to manually cross-reference several screens.

### 1.2 Background / Problem Statement
The university already tracks enrollment, attendance, exam scores, and grading separately (per the BRDs already written for Exam, Grading/GPA, and Attendance). None of these screens currently answer questions like:
- "Which of my advisees are struggling this semester?"
- "Is this student's attendance pattern connected to their falling grades?"
- "Which students are at risk of not returning next semester?"

Right now, answering these requires opening multiple screens per student, one at a time — there is no aggregated, at-a-glance view.

### 1.3 Business Objectives
| # | Objective |
|---|---|
| B1 | Give each advisor a personal dashboard of only their assigned advisees |
| B2 | Surface a computed "academic risk" indicator per student, combining grades, attendance, and other signals |
| B3 | Give Admin/Dean/HOD an aggregated, faculty/department-level view of student performance and retention risk |
| B4 | Reduce the number of screens someone has to open to understand a student's overall standing |
| B5 | Support early intervention — flag at-risk students soon enough for an advisor to act, not after the semester ends |

### 1.4 Stakeholders
| Stakeholder | Interest |
|---|---|
| Academic Advisor (likely a Teacher or a dedicated Advisor role) | Primary user — monitors their assigned advisees |
| Head of Department (HOD) | Department-level rollup of student performance/retention |
| Dean | Faculty-level rollup |
| Admin | Full visibility across all faculties, for institution-wide reporting |
| Student | Out of scope for this phase (see 1.6) — a future "My Progress" view could reuse this data, but isn't part of this capability |

### 1.5 Scope
**In scope:**
- An **Advisor Dashboard**: list/grid of a specific advisor's assigned students, each showing a summary card (current GPA trend, attendance rate, missing/at-risk exam components, an overall risk indicator).
- A **drill-down student view**: click into one student to see the detail behind their risk indicator (grade trend chart, attendance history, exam completion status).
- An **aggregated view** for Admin/Dean/HOD: same risk data, rolled up by department/faculty/program, to answer "how many at-risk students do we have, and where."
- A computed **"Academic Risk" score/flag** per student per semester, combining signals already available in the system (attendance rate, GPA/grade trend, missing exam scores).
- Basic **retention insight**: a simple signal such as "GPA dropped 2+ letter grades since last semester" or "attendance below X% this semester," not a predictive ML model.

**Out of scope (for this phase):**
- Predictive machine-learning dropout modeling — the "risk score" in this phase is a **rules-based** computation, not ML.
- Automated interventions (e.g. auto-emailing at-risk students) — the dashboard surfaces the information; acting on it is manual, for now.
- A student-facing "My Progress" self-service view (may be a future phase, reusing this data).
- Any new data collection — this capability **only aggregates and visualizes existing data** (Enrollment, Attendance, Exam/Grading, Fee status if relevant); it does not introduce new source-of-truth records.

### 1.6 Business Rules
1. An **Advisor** sees only students explicitly **assigned to them** (an advisor-to-student relationship must exist — see Open Questions on how "advisor" is modeled).
2. A student's **Academic Risk** is computed per semester, using at minimum: attendance score (per the Grading & GPA Policy §3.3 formula), current GPA/grade trend (per §5–6 of that same document), and count of missing/ungraded exam components close to their deadline.
3. Risk levels should be simple and actionable: e.g. **On Track / Watch / At Risk**, not a raw unexplained number — an advisor should be able to see *why* a student is flagged, not just that they are.
4. HOD sees the aggregated view for their **department**; Dean for their **faculty**; Admin sees **everything** — this must reuse the same security scoping pattern already established for Attendance, Enrollment, and Staff Attendance (`res.users.teacher_id → teacher → department → faculty`).
5. The dashboard is **read-only** — it visualizes data owned by other models (Attendance, Exam, Enrollment, Grading); it must not become a second source of truth for any of those numbers.
6. Risk computation should be **cached/computed periodically** (e.g. nightly, or on-demand refresh), not recalculated on every page load if it becomes expensive across many students — see Non-Functional Requirements.

### 1.7 Assumptions & Constraints
- This capability depends on the Exam module, Grading & GPA Policy, and Attendance features already being implemented and populated with real data — an empty or partially-built underlying dataset will make the dashboard look broken even if it's built correctly.
- No new "Advisor" model necessarily needs to be created — this may reuse `university.teacher` with an added assignment relationship, but this needs to be confirmed against the actual codebase (see Open Questions).
- Runs on Odoo 19, module `school_management`.

### 1.8 Success Criteria
- An advisor can open the dashboard and, without cross-referencing any other screen, identify which of their advisees need attention this week.
- A Dean/HOD can see, at a glance, how many students in their faculty/department are flagged At Risk, and drill into who they are.
- Risk flags are explainable — clicking one shows the underlying attendance/grade/exam data that produced it.

---

## PART 2 — SYSTEM REQUIREMENTS SPECIFICATION (SRS)

### 2.1 Proposed Data Model

This capability is primarily a **read/aggregation layer**, not a new source of truth. Proposed additions:

**`university.student.advisor`** (new — the advisor assignment link, if one doesn't already exist)
| Field | Type | Notes |
|---|---|---|
| student_id | Many2one → university.student | required |
| advisor_id | Many2one → university.teacher | required |
| academic_year_id | Many2one | so assignments can change year to year |
| active | Boolean | to end an assignment without deleting history |

> Check first whether an advisor relationship already exists on `university.student` (e.g. a field pointing to a teacher) before creating a new model — this may already be covered by existing enrollment or student data.

**`university.student.risk.snapshot`** (new — a computed, periodically-refreshed rollup, one row per student per semester)
| Field | Type | Notes |
|---|---|---|
| student_id | Many2one → university.student | required |
| semester_id | Many2one | required |
| attendance_score | Float | pulled from the Attendance formula (Grading & GPA Policy §3.3) |
| gpa_current | Float | pulled from the student's computed course grades this semester |
| gpa_previous | Float | prior semester's GPA, for trend comparison |
| missing_exam_count | Integer | count of published exams with no score recorded, past their deadline |
| risk_level | Selection | `on_track`, `watch`, `at_risk` — computed from the fields above |
| risk_reason | Char/Text | short human-readable explanation (e.g. "Attendance below 60%, GPA dropped from B to D") |
| computed_at | Datetime | when this snapshot was last refreshed |

- **Why a snapshot table instead of computing live every time:** if risk needs to be computed across hundreds of students on every dashboard load, a stored snapshot (refreshed nightly or on-demand) keeps the dashboard fast — see Non-Functional Requirements.

### 2.2 Functional Requirements

| ID | Requirement |
|---|---|
| FR1 | System shall let an Advisor (teacher with assigned advisees) view a list of only their assigned students |
| FR2 | System shall compute a `risk_level` per student per semester from attendance score, GPA trend, and missing exam count |
| FR3 | System shall display `risk_reason` alongside `risk_level` so the flag is explainable, not a black box |
| FR4 | System shall provide a drill-down view per student showing: attendance history chart, GPA trend chart, and a list of missing/at-risk exam components |
| FR5 | System shall provide an aggregated view for HOD (own department), Dean (own faculty), and Admin (all faculties), showing counts of students per risk level |
| FR6 | System shall allow filtering the aggregated view by program, semester, and risk level |
| FR7 | System shall refresh risk snapshots on a schedule (e.g. nightly cron) rather than recomputing on every page view, with a manual "Refresh now" option for Admin |
| FR8 | System shall never allow editing of underlying Attendance/Exam/Grading data from this dashboard — it is read-only, with links out to the source records if a correction is needed |
| FR9 | System shall show "no advisees assigned" or "insufficient data" states gracefully rather than showing false zeros when underlying data isn't ready |

### 2.3 Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | The aggregated view (potentially hundreds of students) should load from the stored snapshot table, not compute live per request |
| Usability | Visual hierarchy should make "At Risk" students immediately scannable — color coding (e.g. red/amber/green), not just a text label |
| Data integrity | Snapshot computation should be idempotent — re-running it for the same student/semester updates the existing row, not creates duplicates |
| Auditability | `computed_at` timestamp so advisors know how fresh the data is |
| Compatibility | Odoo 19 syntax; reuse existing models rather than duplicating student/attendance/grading data |
| Security | Access strictly scoped per Business Rule 4 — an advisor must never see another advisor's advisees through this dashboard |

### 2.4 Integration Points with Existing Modules

| Existing Module | Integration |
|---|---|
| `university.attendance` | Source of the attendance_score input to risk calculation |
| `university.exam` / `university.exam.score` | Source of missing_exam_count and grade inputs |
| Grading & GPA Policy (final_score, gpa_points) | Source of gpa_current / gpa_previous |
| `university.enrollment` | Confirms which students are actively enrolled this semester (risk snapshots shouldn't include withdrawn students) |
| Security groups (Admin, Dean, HOD, Teacher) | Reused directly for dashboard access scoping |

### 2.5 Security Model (Access Matrix)

| Role | View own advisees | View department rollup | View faculty rollup | View all | Refresh snapshots |
|---|---|---|---|---|---|
| Admin | Yes | Yes | Yes | Yes | Yes |
| Dean | No (unless also an advisor) | No | Yes (own faculty) | No | No |
| HOD | No (unless also an advisor) | Yes (own department) | No | No | No |
| Teacher (as Advisor) | Yes (own advisees only) | No | No | No | No |

### 2.6 Open Questions (to confirm before build)
1. **Is "Advisor" a distinct concept in the current codebase**, or does every teacher automatically advise the students in the sections they teach? If the latter, the advisor-assignment model in §2.1 may be unnecessary — advisees could simply be derived from `university.enrollment` + `section_id.teacher_ids`.
2. **What counts as "retention risk" specifically?** The BRD assumes attendance + GPA trend + missing exams — is there a more specific definition the university already uses (e.g. a formal early-warning policy)?
3. **How fresh does the data need to be?** Nightly snapshot refresh assumed — would advisors need something closer to real-time (e.g. right after a teacher publishes new exam scores)?
4. **Should Dean/HOD who are *also* advisors see both their personal advisee list and their aggregated rollup**, or are these mutually exclusive roles in practice?
5. **Does a "watch" vs. "at risk" threshold need to be configurable** (e.g. per program, since some programs may have different normal attendance/grade baselines), or is one fixed threshold acceptable for the whole university?

---

## Suggested Build Order
1. Confirm advisor relationship (new model vs. derived from enrollment) — resolves Open Question 1 first, since it changes the data model
2. `university.student.risk.snapshot` model + computation logic (attendance + GPA + missing exams → risk_level)
3. Scheduled action (cron) to refresh snapshots, plus a manual "Refresh now" for Admin
4. Advisor Dashboard view (own advisees, risk cards, drill-down)
5. Aggregated view for HOD/Dean/Admin (rollup by department/faculty, filterable)
6. Security groups/rules reusing the existing Admin/Dean/HOD/Teacher scoping pattern
