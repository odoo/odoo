# Transcript Requests & Academic Risk Integration — University Project (Odoo 19)
### How the Transcript Request feature interacts with the Student Analytics & Advisor Dashboard

---

## 1. Purpose
Define whether, and how, a student's **academic risk status** (from the Student Analytics & Advisor Dashboard) and **incomplete grade data** should affect their ability to request an official transcript — and what an advisor should see when one of their at-risk advisees requests one.

This document sits between two existing docs and reconciles them:
- `Grading_GPA_Policy.md` §9 — Transcript Request Policy (one request per semester, blocked while grades are "In Progress")
- `Student_Analytics_Advisor_Dashboard_BRD_SRS.md` — the risk-flagging system (`on_track` / `watch` / `at_risk`)

---

## 2. The Core Distinction: "Hard Block" vs. "Soft Flag"

These two concerns are **not the same thing** and should not be conflated into one rule:

| | Incomplete Grades | Academic Risk |
|---|---|---|
| **What it means** | A component (quiz/midterm/final/assignment) hasn't been published yet | A computed indicator combining attendance, GPA trend, and missing exams |
| **Should it block a transcript?** | **Yes — hard block.** A transcript can't accurately report a grade that doesn't exist yet. | **No — not by itself.** Being flagged "At Risk" is about academic performance, not data completeness. Blocking a transcript because a student is struggling would be punitive, not a data-integrity issue. |
| **Existing rule** | Already defined in `Grading_GPA_Policy.md` §9.3.2 | Not yet defined — this document proposes a **notification**, not a block |

**Recommendation:** keep the hard block exactly as already specified (incomplete grades block issuance). Do **not** block a transcript request just because a student is flagged "At Risk" — instead, surface it as information for the advisor.

---

## 3. Proposed Behavior

### 3.1 Hard block (unchanged from existing policy)
If any grade component for the requested semester is not yet published/finalized, the transcript request is rejected with a clear message — this was already defined and doesn't change here.

### 3.2 Soft flag (new — the actual integration point)
When a student submits a transcript request:
1. The system checks the student's latest `university.student.risk.snapshot` for that semester.
2. If `risk_level = at_risk` or `watch`, the request still proceeds normally (assuming grades are complete) — **but** the student's assigned Advisor (and optionally HOD) receives a notification: *"[Student] requested a transcript for [Semester] while flagged [At Risk / Watch]."*
3. This is purely informational — it does not delay or block the transcript. It exists so an advisor doesn't lose track of a struggling student who may be about to transfer, withdraw, or graduate without the advisor having had a chance to intervene.

### 3.3 A third, genuinely separate concept: Academic/Financial Holds
Some institutions **do** legitimately block transcripts for reasons unrelated to grade completeness — most commonly an **unpaid fee balance** (this connects to the Finance flow diagram from earlier, where the link between Payment status and Grading/Transcript was flagged as "unconfirmed"). If your university has this kind of hold, it should be modeled as its own explicit concept — **not** reused from the risk system — because a fee hold is an administrative block, not an academic performance signal.

---

## 4. Data Model Additions

**On `university.transcript.request` (extends the model from `Grading_GPA_Policy.md` §9.2):**
| Field | Type | Notes |
|---|---|---|
| risk_level_at_request | Selection | snapshot of the student's risk level at the moment of request, for advisor visibility and later reporting — not recomputed after the fact |
| advisor_notified | Boolean | whether the soft-flag notification (3.2) was sent |
| hold_id | Many2one → university.academic.hold (new, optional) | if a hold model exists/gets built, link it here; null if no hold applies |

**`university.academic.hold`** (new — only if your university actually has this concept; otherwise skip)
| Field | Type | Notes |
|---|---|---|
| student_id | Many2one → university.student | required |
| hold_type | Selection | `fee_balance`, `disciplinary`, `other` |
| active | Boolean | whether the hold currently blocks transcript issuance |
| placed_by | Many2one → res.users | who placed the hold |
| note | Text | reason |

---

## 5. Functional Requirements

| ID | Requirement |
|---|---|
| FR1 | System shall check for incomplete grade components before allowing a transcript request, per existing policy — unchanged |
| FR2 | System shall check the student's current risk snapshot at time of request and record `risk_level_at_request` on the transcript request record |
| FR3 | System shall notify the student's assigned advisor (and HOD, if configured) when a transcript request is submitted by a student flagged `at_risk` or `watch` — notification only, no blocking |
| FR4 | System shall NOT use risk_level as a blocking condition for transcript issuance under any circumstance in this phase |
| FR5 | If an `university.academic.hold` model exists and is active for the student, system shall block the transcript request with a message identifying the hold type, separately from the grade-completeness check |
| FR6 | Advisor Dashboard (from the existing BRD/SRS) shall show a small indicator on a student's card if they have a pending or recent transcript request, so the advisor has context without needing to check a separate screen |

---

## 6. Open Questions
1. **Does this university actually use academic/financial holds** (fee-based or disciplinary) that block transcripts? If not, section 3.3 and the `university.academic.hold` model can be dropped entirely — don't build it speculatively.
2. **Who receives the soft-flag notification** — the advisor only, or also HOD/Dean? Should it be an in-app notification, an email, or both?
3. **Should the risk snapshot used for `risk_level_at_request` be the most recent one available, or specifically the one computed at semester-end** (closer to when grades are finalized) — these could differ if the student's risk changed between mid-semester and the request date?
4. **Should a transcript request itself factor into the risk calculation** (e.g. a sudden transcript request could itself be a transfer/withdrawal signal worth flagging), or is that out of scope and overengineering for this phase?

---

## 7. Explicit Non-Goal
This document intentionally does **not** propose blocking transcripts for academic risk. If your institution's actual policy requires that (e.g. a formal academic probation status that does block transcripts), that would need to be modeled as its own distinct status — separate from the dashboard's "at risk" indicator — and should be raised as a new, explicit business rule rather than silently reusing the dashboard's risk flag for an access-control decision it wasn't designed for.
