# Benchmark: How International Universities Manage Grading & Attendance
### Research reference for the University Project's Grading & GPA Policy

---

## 1. Purpose
This document summarizes real-world attendance and grading practices from various universities, gathered to benchmark the weights and rules proposed in `Grading_GPA_Policy.md`. It is a reference, not a finalized policy — use it to validate or adjust the earlier assumptions.

---

## 2. Attendance Deduction Patterns

### 2.1 Percentage-per-absence deductions
A 1% deduction from the overall final grade per unexcused absence is common practice. NYU London applies a similar rule, scaled to how often the class meets:
- Classes meeting once a week: 2% deducted per unexcused absence
- Classes meeting twice a week: 1% deducted per unexcused absence

**Comparison:** the project's current rule (flat 1% per absence-equivalent, out of a 10% attendance weight) matches this pattern closely.

### 2.2 "N lates = 1 absence" conversion
Several institutions convert repeated lateness into a full absence. One documented policy states that arriving late to class three times counts as one absence.

**Comparison:** the project's rule (4 lates = 1 absent equivalent) is the same mechanic, just a slightly higher threshold (4 instead of 3).

### 2.3 Free/tolerance absences before penalties start
Many syllabi allow a small number of absences before any grade penalty begins:
- Some courses give two unpenalized absences before deductions start
- One writing-course policy: 1–2 absences still earn full attendance credit (A), grade drops in steps at 3, 5, and 6+ absences, with 7+ treated as excessive (withdrawal territory)

**Comparison:** the project currently has no "free" absence buffer — every absence (after equivalence conversion) deducts 1% immediately. Adding a small tolerance (e.g. first absence free) is a common softer alternative, worth considering as a configurable option.

### 2.4 Excused vs. unexcused distinction
Nearly every policy reviewed distinguishes **excused** (permission-based) absences from **unexcused** ones, and only unexcused absences trigger a grade penalty. Excused absences typically require pre-approval or documentation.

**Comparison:** the project's "Permission" category already reflects this distinction — 2 permissions = 1 absent equivalent softens the penalty rather than removing it entirely, which is a reasonable middle ground between "excused = free" and "excused = same as absent."

---

## 3. Exam / Quiz / Assignment Weighting Patterns

**Key finding: there is no single universal standard.** Weighting varies significantly by country, institution, and even individual instructor. Examples found:

| Institution / Course type | Weight breakdown |
|---|---|
| Math course (US) | 10% Homework, 15% Quizzes (best-N scores only), 25% Midterm, 50% Final |
| Computer Science course (US) | 10% Quizzes & Attendance, 20% Homework, 28% Programming Assignments, 20% Midterm, 22% Final |
| Engineering course (Canada, York University) | 2% intro quiz + 40% across 4 quizzes, 25% Midterm, 33% Final |
| Engineering course, variant (York University) | 10% Assignments, 20% Labs, 15% In-class quizzes, 20% Midterm, 35% Final |
| **Philippine / Southeast Asian (CHED/DepEd-style) model** | Overall grade = 40% Midterm period + 60% Final period. Each period itself = 40% Exam + 30% Quizzes/Written Work + 20% Projects/Course Output + 10% Participation |
| Physics/astronomy course (US) | 5% Participation, 15% Quizzes (6), 25% Homework (6), 15% Midterm, 15% Term Project, 25% Final |

### 3.1 Relevance to this project
The **Philippine/Southeast Asian model** is structurally the closest match to what's being built here — it also splits the semester into a Midterm period and a Final period, each built from an exam + quizzes + coursework + participation, rather than one flat list of weighted components. This is worth considering if the university follows a regional (ASEAN-influenced) academic structure rather than a US-style single-semester weighting.

### 3.2 Comparison to the project's current split
The project's proposed weighting (Attendance 10% / Quiz+Midterm combined 30% / Assignment 10% / Final Exam 50%) sits within the realistic range found above. A 50% final-exam weight is on the heavier end but is not unusual — one math course syllabus uses exactly 50% for the final, with 25% Midterm and 15% Quizzes.

---

## 4. GPA / Letter Grade Scale Variation

No universal cutoff table exists — every institution sets its own. Examples found:

| Scale A | Scale B |
|---|---|
| A: 90–100, B: 80–89, C: 70–79, D: 60–69, F: below 60 | A: 87.5%+, B: 75–87.5%, C: 62.5–75%, D: 50–62.5%, F: below 50% |

Some departments also use finer-grained letter bands (A+, A, A−, B+, B, B−, etc.) mapped to numeric GPA points, as referenced in the project's `Grading_GPA_Policy.md` §6.

**Conclusion:** the GPA table in the Grading & GPA Policy document is a reasonable placeholder, but the actual cutoffs should be set to match the university's own academic regulations, not copied from any single external source.

---

## 5. Recommendations for the Project

1. **Attendance rules** — the current 1%-per-absence and 4-lates-equals-1-absence rules are consistent with common practice; no change needed. Consider adding an optional "first absence free" tolerance if the university wants a softer policy.
2. **Weighting split** — the current 10/30/10/50 split is realistic. If the university's academic structure follows a regional Midterm/Final period model (like the Philippine example), consider restructuring the formula around two periods instead of five flat components — this would be a more significant redesign and should be confirmed first.
3. **GPA scale** — finalize actual cutoffs based on the university's own academic regulations rather than the placeholder table.
4. **Excused absence handling** — keep "Permission" as a softening mechanic (2 permissions = 1 absent) rather than either full exemption or full penalty, which matches common practice.

---

## 6. Sources Referenced
- University of Illinois — attendance policy compilation (odos.illinois.edu)
- Marshall University / College of Fine Arts — attendance policy statements
- NYU London — attendance policy
- UMass Boston — inclusive attendance policy guidance
- Carnegie Mellon University, Eberly Center — attendance policy samples
- DePaul University — attendance, participation & late work policies
- University of Georgia (course grading change notice)
- University of Maryland (Astronomy course syllabus)
- York University (EECS course grading pages, two course years)
- Georgia Tech (course assignment weighting page)
- University of Washington (Math course syllabus)
- Scribd — "Grading System for Midterms and Finals" (Philippine/CHED-style model)
