# Quiz Deadline & Session Rules — University Project (Odoo 19)
### How a Quiz's timing, deadline, and late submission work

---

## 1. Purpose
Define exactly how a Quiz session opens, closes, and handles a deadline — including auto-created quizzes (triggered by the Timetable) and manually created quizzes (teacher-set windows), and what happens when a student submits late.

---

## 2. Two Ways a Quiz Gets Its Timing

### 2.1 Auto-created Quiz (default path — see Exam BRD/SRS §2.1.1)
- The moment a class session's `start_time` is reached in `university.timetable`, a scheduled action (cron) auto-creates the quiz with `state = open`.
- `end_time` defaults to the timetable slot's own `end_time` — the quiz session is tied to the length of the class period itself.
- No manual setup required. It opens when class starts and closes (by default) when class ends.
- Only fires for sections/subjects currently in an **active semester** (`semester.start_date ≤ today ≤ semester.end_date`) — see Exam BRD/SRS §2.1a.

### 2.2 Manually created Quiz (teacher-set deadline)
- Teacher sets `start_time` and `end_time` directly.
- Two common patterns:
  - **Timed in-class quiz:** e.g. opens 9:00 AM, closes 9:20 AM (20-minute window).
  - **Take-home / open-window quiz:** e.g. opens Monday, due Friday 11:59 PM (multi-day window).
- `duration_minutes` (optional) caps how long a **student** has once they personally start the quiz, even if the overall window is longer — e.g. the window is open for 3 days, but each student only gets 15 minutes from the moment they click "Start."

---

## 3. Fields Governing Deadline Behavior

| Field | Model | Role |
|---|---|---|
| `start_time` | `university.exam` | When the quiz becomes available |
| `end_time` | `university.exam` | The hard deadline — after this, the session is considered closed |
| `duration_minutes` | `university.exam` | Optional per-student time limit once they start (independent of the overall window) |
| `late_submission_allowed` | `university.exam` | If **False**, nothing submitted after `end_time` counts |
| `late_penalty_percent` | `university.exam` | If late submission is allowed, this % is deducted from the score |
| `submitted_at` | `university.exam.score` | Timestamp of the student's actual submission |
| `is_late` | `university.exam.score` (computed) | `True` if `submitted_at > exam_id.end_time` — computed automatically |

---

## 4. What Happens at the Deadline

| Scenario | Outcome |
|---|---|
| Student submits before `end_time` | Normal score, `is_late = False` |
| Student submits after `end_time`, `late_submission_allowed = True` | Score accepted, `is_late = True`, `late_penalty_percent` deducted automatically |
| Student submits after `end_time`, `late_submission_allowed = False` | Submission rejected / not recorded — or recorded as absent, depending on policy (see Open Questions) |
| No submission at all by `end_time` | Student can be marked absent for the quiz, contributing 0 to that component unless a make-up policy applies |

### Worked Example
- Quiz deadline (`end_time`): 10:00 AM
- Student submits at: 10:07 AM → `is_late = True`
- `late_submission_allowed = True`, `late_penalty_percent = 10`
- Raw score: 80/100 → **Final recorded score: 72/100** (80 − 10% penalty)

If `late_submission_allowed` had been `False`, the 10:07 AM submission would be rejected entirely rather than penalized.

---

## 5. State Transitions

```
draft → scheduled → open → closed → grading → published
```

- `open` — between `start_time` and `end_time`; students can submit.
- `closed` — past `end_time`; no new submissions unless late submission is explicitly allowed.
- `grading` — teacher is entering/reviewing scores.
- `published` — scores visible to students; locked from further edits except by Admin.

---

## 6. Open Question: Automatic vs. Manual Close

The `open → closed` transition can work one of two ways — **this needs to be decided before build:**

| Option | Behavior |
|---|---|
| **A — Automatic (cron-driven)** | A scheduled action checks every few minutes and flips `state` to `closed` the instant `end_time` passes. Guarantees the deadline is enforced exactly, even if no one is watching. |
| **B — Manual (teacher-driven)** | The system flags the quiz as "overdue" once `end_time` passes, but stays `open` until the teacher manually closes it. Gives teachers flexibility (e.g. to extend a deadline on the fly) but relies on them to act. |

**Recommendation:** Option A for strict deadlines (timed quizzes), Option B for take-home style quizzes where a teacher might want to extend the window. This could be a per-quiz toggle (`auto_close = True/False`) rather than a single global rule.

---

## 7. Open Questions
1. Should a same-semester quiz's `end_time` ever exceed the semester's `end_date`? (Should be blocked or auto-adjusted.)
2. When `late_submission_allowed = False` and a student misses the deadline entirely, should they be recorded as **Absent** (0 score) automatically, or left ungraded until the teacher manually decides?
3. Should `duration_minutes` (per-student timer) be enforced client-side only, or does it need a server-side check (submission timestamp minus start timestamp) to prevent a student from bypassing a client-side timer?
4. Is a grace period needed (e.g. 1–2 minutes tolerance) before something counts as "late," to account for network/submission lag?
