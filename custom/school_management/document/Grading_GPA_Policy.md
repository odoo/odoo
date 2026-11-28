# Grading & GPA Policy — University Project (Odoo 19)
### Attendance-Weighted Course Grade & GPA Calculation

---

## 1. Purpose
Define how a student's final course score and GPA are calculated from four inputs: **Attendance**, **Quiz + Midterm**, **Assignment**, and **Final Exam** — and how attendance itself is scored using permission/late/absent equivalence rules.

---

## 2. Grade Components & Weights

| Component | Weight |
|---|---|
| Attendance | 10% |
| Quiz + Midterm (combined) | 30% |
| Assignment | 10% |
| Final Exam | 50% |
| **Total** | **100%** |

> ⚠️ **Assumption flagged:** your message groups Quiz + Midterm together under one 30%, but doesn't say how that 30% splits between the two. I've assumed **Quiz 10% / Midterm 20%** below as a placeholder — confirm or give me the real split (see Open Questions).

| Sub-component (assumed split) | Weight |
|---|---|
| Quiz | 10% |
| Midterm Exam | 20% |
| *(Quiz + Midterm subtotal)* | *30%* |
| Assignment | 10% |
| Final Exam | 50% |
| Attendance | 10% |

---

## 3. Attendance Scoring Rules

### 3.1 Definitions
| Status | Meaning |
|---|---|
| Present | Attended normally |
| Late | Arrived after the session started |
| Permission | Pre-approved excused absence |
| Absent | Unexcused absence |

### 3.2 Equivalence Rules
| Rule | Effect |
|---|---|
| **2 Permissions** | = **1 Absent** equivalent |
| **4 Lates** | = **1 Absent** equivalent |
| **Each Absent** (real or converted) | **−1%** from the Attendance score |

### 3.3 Formula
```
effective_absences = actual_absents
                    + FLOOR(total_permissions / 2)
                    + FLOOR(total_lates / 4)

attendance_score (%) = MAX(0, 10 − effective_absences × 1)
```
- Attendance score is capped at a **minimum of 0** — it cannot go negative even with many absences.
- Attendance score is capped at a **maximum of 10** (its full weight) — a perfect record contributes the full 10%, never more.
- `FLOOR()` means partial counts don't convert yet: 1 permission or 3 lates alone don't count as an absent equivalent — only every full pair (permissions) or full group of four (lates) does.

### 3.4 Worked Example
A student has: 3 real absents, 5 permissions, 7 lates.
```
effective_absences = 3 + FLOOR(5/2) + FLOOR(7/4)
                    = 3 + 2 + 1
                    = 6

attendance_score = MAX(0, 10 − 6) = 4%   (out of the 10% attendance weight)
```

---

## 4. Exam & Assignment Scoring

Each component is entered as a raw score out of its own max (e.g. Quiz out of 100, Midterm out of 100, Assignment out of 100, Final out of 100), then converted to its weighted percentage:

```
component_percent = (raw_score / max_score) × component_weight
```

| Component | Example raw score | Max | Weight | Weighted contribution |
|---|---|---|---|---|
| Quiz | 85 | 100 | 10% | 8.5% |
| Midterm | 78 | 100 | 20% | 15.6% |
| Assignment | 90 | 100 | 10% | 9.0% |
| Final Exam | 72 | 100 | 50% | 36.0% |
| Attendance | (see §3.3) | 10 | 10% | 4.0% (from example above) |

---

## 5. Final Course Score

```
final_score (%) = attendance_score
                 + quiz_percent
                 + midterm_percent
                 + assignment_percent
                 + final_percent
```

Using the worked example above:
```
final_score = 4.0 + 8.5 + 15.6 + 9.0 + 36.0 = 73.1%
```

---

## 6. GPA Conversion Table (standard 4.0 scale — adjust to your institution's actual scale)

| Score Range | Letter Grade | GPA Points |
|---|---|---|
| 90–100 | A | 4.0 |
| 85–89 | A− | 3.7 |
| 80–84 | B+ | 3.3 |
| 75–79 | B | 3.0 |
| 70–74 | B− | 2.7 |
| 65–69 | C+ | 2.3 |
| 60–64 | C | 2.0 |
| 55–59 | C− | 1.7 |
| 50–54 | D | 1.0 |
| Below 50 | F | 0.0 |

Using the example: **73.1% → B− → 2.7 GPA points** for this course.

**Overall semester GPA** = credit-weighted average of each course's GPA points:
```
semester_GPA = Σ (course_GPA_points × course_credit_hours) / Σ (course_credit_hours)
```

---

## 7. Data Model Additions

**On `university.enrollment` (or a new `university.course.grade` per student/subject/semester):**
| Field | Type | Notes |
|---|---|---|
| attendance_score | Float | computed from §3.3, 0–10 |
| quiz_percent | Float | computed |
| midterm_percent | Float | computed |
| assignment_percent | Float | computed |
| final_exam_percent | Float | computed |
| final_score | Float | computed, sum of the above, 0–100 |
| letter_grade | Selection/Char | computed from §6 |
| gpa_points | Float | computed from §6 |

**On `university.semester` or `university.academic_record`:**
| Field | Type | Notes |
|---|---|---|
| semester_gpa | Float | computed, credit-weighted average per §6 |

---

## 8. Business Rules
1. Attendance counts (`actual_absents`, `total_permissions`, `total_lates`) are pulled from `university.attendance` records for that student/subject/semester — not entered manually.
2. `quiz_percent` and `midterm_percent` pull from published `university.exam.score` records of type `quiz` and `midterm` respectively (per the Exam module BRD/SRS).
3. `final_exam_percent` pulls from the published `final` exam score.
4. `assignment_percent` pulls from the assignment grading model (existing `grading`/`assignment` module) — confirm its scoring scale matches (0–100).
5. `final_score` recomputes automatically whenever any input (attendance, quiz, midterm, assignment, final) changes.
6. GPA and letter grade are only finalized once **all** components are published/closed for that subject/semester — a partial grade should show as "In Progress," not a misleading final letter grade.
7. Weight percentages (10/30/10/50, and the internal 10/20 quiz/midterm split) should be configurable per subject or program in case different courses use different weighting — not hardcoded, in case policy changes later.

---

## 9. Open Questions
1. **Quiz vs. Midterm split** — is it 10%/20% as assumed, or a different split (e.g. 15%/15%)? If there are multiple quizzes per semester, do their scores average together before applying the 10%?
2. **"Permission"** — is this the same as a pre-approved leave/excuse request, and does it need its own approval workflow (e.g. Dean/Head of Faculty approves it) before it counts toward the 2-permission rule?
3. **GPA scale** — does your institution use a specific existing scale (e.g. 4.0, 4.3, or a percentage-only system with no letter grades)? The table in §6 is a placeholder.
4. **Rounding** — should `final_score` and `gpa_points` round to 1 decimal, 2 decimals, or use a specific rounding method (nearest, floor, standard rounding)?
5. **Multiple quizzes** — if a subject runs several quizzes across the semester (per the auto-created "plain exam" flow), is the 10% Quiz weight based on the **average of all quizzes**, or only a specific designated one?
