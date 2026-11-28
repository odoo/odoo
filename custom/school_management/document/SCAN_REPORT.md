# School Management Scan Report

## Summary

This report applies the module scan prompt to `school_management` on Odoo 19.0.

The module is broad and already has useful professional foundations: role groups, many ACL lines, record rules for students/teachers/HOD/dean/admin, migrations, server-side constraints for enrollment capacity and period consistency, mail tracking on important documents, tests, and backend dashboard assets.

The most important risks are security and lifecycle consistency:


- Some teacher-writable teaching models have broad ACLs without matching teacher record rules.
- `record_rules.xml` repeats XML IDs for administrator rules, so later records silently replace earlier definitions.
- Admission, fee, payment, grading, and reporting actions need stricter state-machine guards.
- Two admission pipeline models exist in files but are not imported, not loaded by the manifest, and have no access rules.

No production business code was changed by this scan. The only change made is this report file.

## Inventory

### Module

| Item | Value |
|---|---|
| Module | `school_management` |
| Odoo | `19.0` |
| Manifest version | `19.0.1.2.1` |
| Depends | `auth_signup`, `base`, `mail`, `portal`, `web` |
| Assets bundle | `web.assets_backend` |
| Security files | `../security/security.xml`, `security/ir.model.access.csv`, `security/record_rules.xml` |
| Migrations found | `../migrations/19.0.1.2.0/pre-migrate.py`, `migrations/19.0.1.2.1/pre-migrate.py` |
| Test files found | settings, payment, signup, enrollment, integrity, security menus, document signatures, capability, user provisioning |

### Models

| Model | File | Notes |
|---|---|---|
| `university.faculty` | `../models/faculty.py` | Faculty state and scoped department/teacher/student/program aggregates |
| `university.department` | `../models/department.py` | Departments, head assignment, programs, teachers, subjects |
| `university.program` | `../models/program.py` | Programs/majors, subjects, curriculum report actions |
| `university.academic.year` | `../models/academic_year.py` | Academic year date constraints and current-year guard |
| `university.semester` | `../models/academic_year.py` | Semester date constraints |
| `university.semester.subject` | `../models/semester_subject.py` | Unique semester-subject offering guard |
| `university.teacher` | `../models/teacher.py` | Academic staff, login creation/reset |
| `university.student` | `../models/student.py` | Student profile, enrollment/payment actions, login creation/reset |
| `university.subject` | `../models/subject.py` | Subjects, linked programs, teachers, sections |
| `university.classroom` | `../models/classroom.py` | Classrooms |
| `university.class.section` | `../models/class_section.py` | Program/subject sections, capacity and teacher/subject guards; assignment context inheritance |
| `university.enrollment` | `../models/enrollment.py` | Student enrollment, unique indexes, capacity row lock |
| `university.fee` | `../models/fee.py` | Fee invoice, chatter, posting/cancel/payment balance state |
| `university.fee.line` | `../models/fee.py` | Invoice fee lines |
| `university.fee.structure` | `../models/fee.py` | Fee templates |
| `university.fee.structure.line` | `../models/fee.py` | Fee template lines with non-negative amount constraint |
| `university.payment` | `../models/payment.py` | Student payments, posting/cancel/draft, overpayment guard |
| `school.dashboard` | `../models/dashboard.py` | Dashboard metrics/actions |
| `university.academic.assignment` | `../models/academic_assignment.py` | HOD/dean/staff role assignment consistency |
| `university.document.signature` | `../models/document_signature.py` | Student/fee document signatures |
| `university.capability` | `../models/capability.py` | Capability roadmap/configuration |
| `university.lesson.plan` | `../models/lesson_plan.py` | Teacher lesson plans |
| `university.assignment` | `../models/assignment.py` | Assignments and approval flow; auto-inherits teacher/subject from section in create() |
| `university.assignment.submission` | `../models/assignment.py` | Submissions and grading result creation |
| `university.timetable.slot` | `../models/timetable.py` | Timetable slots and resource conflicts |
| `university.timeslot` | `../models/timetable.py` | Reusable class time slots |
| `university.notice.board` | `../models/notice_board.py` | Notices |
| `university.service.hour` | `../models/service_hour.py` | Service-hour approvals |
| `university.attendance` | `../models/attendance.py` | Attendance records |
| `university.admission.application` | `../models/admission.py` | Admission applications, confirmation, student/enrollment/fee creation |
| `university.grade.scale` | `../models/grading.py` | Grade scale |
| `university.grade.scale.line` | `../models/grading.py` | Grade ranges |
| `university.assessment.category` | `../models/grading.py` | Assessment weights |
| `university.assessment.result` | `../models/grading.py` | Scores and publishing |
| `university.report.card` | `../models/grading.py` | Report card generation/approval |
| `university.report.card.line` | `../models/grading.py` | Report card lines |
| `university.transcript` | `../models/grading.py` | Transcript generation/approval |
| `university.transcript.line` | `../models/grading.py` | Transcript lines |
| `admission.lead` | `../models/admission_lead.py` | Not imported by `../models/__init__.py`; no ACL |
| `admission.stage` | `../models/admission_stage.py` | Not imported by `../models/__init__.py`; no ACL |

### Wizards

| Wizard | File | Main action |
|---|---|---|
| `university.student.enrollment.wizard` | `../wizard/student_enrollment_wizard.py` | `action_register_enrollments` |
| `university.bulk.enrollment.wizard` | `../wizard/bulk_enrollment_wizard.py` | `action_enroll_students` |
| `university.populate.class.wizard` | `../wizard/populate_class_wizard.py` | `action_populate_class` |
| `university.teacher.account.wizard` | `../wizard/teacher_account_wizard.py` | `action_create_accounts` |
| `university.timetable.generation.wizard` | `../wizard/timetable_generation_wizard.py` | `action_generate_timetable` |

### Views, Actions, Menus, Reports

The manifest loads the main view files for faculties, departments, programs, academic years, semester subjects, classrooms, admissions, subjects, class sections, academic assignments, teachers, students, settings, capabilities, grading, enrollment, fees, payments, signatures, dashboard shell actions, teacher dashboard shell actions, lesson plans, assignments, timetable, attendance, academic reports, and menus.

Reports found:

- Payment receipt: `../reports/payment_report.xml`, `reports/payment_report_template.xml`
- Curriculum reports: `../reports/curriculum_report.xml`, `reports/curriculum_report_template.xml`
- Academic report card/transcript: `../reports/academic_reports.xml`, `reports/academic_report_templates.xml`

Loaded menus are organized in `../views/menu_views.xml`. Frontend assets are loaded through `web.assets_backend`.

### Security

Groups:

- `group_school_user`
- `group_school_student`
- `group_school_teacher`
- `group_teacher_dashboard`
- `group_school_hod`
- `group_school_dean`
- `group_school_admin`
- `group_student_portal`

ACL coverage:

- Almost all loaded `university.*` models have access rows.
- `school.dashboard` has read-only access for admin/system/school users/teachers.
- `admission.lead` and `admission.stage` have no ACL rows, but they are also not currently imported or loaded.

Record rules:

- Student and portal rules restrict own profile, enrollment, fee, payment, attendance, assignments, submissions, report cards, transcripts.
- Teacher rules exist for teacher profile, academic assignments, own class sections, own subjects, students in own sections, and enrollments in own sections.
- HOD and dean rules scope teachers, subjects, students, sections, assignments, and enrollments by department/faculty.
- Administrator override rules exist, but several XML IDs are duplicated later in the same file.

### Main Data Flows

Student registration:

1. Student record is created in `university.student`.
2. Admin action `action_create_user` creates or links `res.users`.
3. Student signup override in `res.users._signup_create_user` links a user to a matching student email.
4. Student can access own records through student/portal record rules.

Enrollment:

1. Enrollment can be created directly, through `student_enrollment_wizard`, `bulk_enrollment_wizard`, class populate wizard, or admission confirmation.
2. `university.enrollment.create` checks class capacity and active program-period duplicates.
3. SQL unique indexes backstop duplicate section enrollments and active program-period enrollments.
4. Period and section/program consistency constraints validate selected academic year, semester, program, and section.

Admission:

1. Application is created in `university.admission.application`.
2. User can submit, approve, reject, cancel, reset, or confirm using object actions.
3. Confirmation requires approved state.
4. Confirmation creates or updates the student, creates or reuses enrollment, and generates a posted fee when a fee structure exists.

Fee and payment:

1. Fee structures prepare fee invoice lines.
2. Fee invoice posts from draft when it has lines.
3. Payment posting validates positive amount, student/fee consistency, and overpayment.
4. Posted payments update the fee invoice state to paid/posted based on balance.
5. Payment receipt email is attempted when a fee becomes fully paid.

Dashboard reporting:

1. Owl dashboard calls `school.dashboard.get_dashboard_data`.
2. Server methods use search counts, grouped reads, and safe fallbacks.
3. Data is filtered by selected academic year and semester where supported.

## Findings Table

| ID | Area | Severity | Location | Problem | Impact | Fix | Effort |
|---|---|---|---|---|---|---|---|
| R-01 | B | Critical | `models/student.py:222-233`, `models/teacher.py:206-224`, `models/student.py:257`, `models/teacher.py:247` | User creation and password reset write the literal password `password123`, and notifications expose it. | Real student/teacher accounts can be compromised easily; shared default passwords are a serious production security risk. | Generate signup/reset tokens or use Odoo's reset-password email flow. Do not store or display a shared default password. | Medium |
| R-02 | B | High | `../security/ir.model.access.csv`, `security/record_rules.xml` | Teachers have create/write access to `university.lesson.plan`, `university.assignment`, `university.assignment.submission`, `university.attendance`, and related teaching models, but record rules are missing or incomplete for teacher ownership on several of them. Evidence: no `model_university_lesson_plan` rule; assignment rules only found for students. | A teacher may read or modify academic records outside their own classes, depending on the model. | Add teacher-scoped record rules for lesson plans, assignments, submissions, attendance, assessment results, and service hours. Add tests with two teachers in different sections. | Medium |
| R-03 | B | High | `security/record_rules.xml:428`, `439`, `450`, `461`, `505`, and later `591`, `602`, `613`, `624`, `646` | XML IDs such as `rule_admin_all_students`, `rule_admin_all_departments`, `rule_admin_all_programs`, `rule_admin_all_subjects`, and `rule_admin_all_enrollments` are defined twice. | Later XML records silently update earlier rules, making security hard to reason about and changing unlink behavior from false to true in some admin overrides. | Keep one record per XML ID. Rename intentional extra rules or merge them into one clear administrator override policy. | Small |
| R-04 | B | High | `../models/admission_lead.py`, `models/admission_stage.py`, `models/__init__.py`, `__manifest__.py`, `security/ir.model.access.csv` | `admission.lead` and `admission.stage` are present as Python/XML/data files but are not imported, not loaded by the manifest, and have no ACL rows. | The pipeline feature is dead code today; loading its view later would fail because models/actions/security are incomplete. | Either remove the dead files or fully wire them into `../models/__init__.py`, manifest data, ACLs, record rules, and menus. | Small |
| R-05 | A | High | `models/fee.py:154-170`, `models/payment.py:107-129` | Fee and payment state actions are too permissive. Fee can be reset to draft from any state; payment can be posted/canceled/reset without checking the prior state. | Users can reopen paid/canceled documents and make financial states inconsistent. | Define allowed transitions: fee draft -> posted -> paid/canceled, payment draft -> posted -> canceled, with reset only for admin and only where safe. | Medium |
| R-06 | A | High | `models/admission.py:124-149` | Admission actions `submit`, `approve`, `reject`, `cancel`, and `reset_to_draft` write states directly without validating the current state. Only `action_confirm` checks for approved state. | Applications can jump between states in ways the UI probably did not intend, such as approving a cancelled or rejected application. | Add explicit transition guards and tests for forbidden transitions and double-click behavior. | Medium |
| R-07 | D | Medium | `models/fee.py:206-303` | `university.fee.line.amount` has no non-negative constraint, although fee structure lines do. | A direct invoice line can use a negative amount and reduce invoice totals without a clear credit-note flow. | Add an amount constraint to `university.fee.line` or implement a deliberate credit/refund document type. | Small |
| R-08 | D | Medium | `models/grading.py:178-236`, `models/grading.py:282-331` | Report card and transcript generation replaces lines and marks records generated, but approval does not lock regeneration or editing. | Approved academic records may be regenerated or edited after approval, weakening transcript integrity. | Block line regeneration and sensitive edits after approval; use chatter/tracking and admin-only reset. | Medium |
| R-09 | C | Medium | `models/faculty.py:92-114`, `models/department.py:77-92`, `models/assignment.py:58-61`, `../models/dashboard.py` | Several count computations use `len(mapped(...))` or One2many lengths, which can load many records. Dashboard code is better, but list-view counts may still grow expensive. | Large datasets can make faculty/department/staff screens slow. | Use `read_group` or stored counters for hot counts, especially for students, enrollments, and submissions. | Medium |
| R-10 | D | Medium | Multiple Many2one fields across `fee.py`, `payment.py`, `admission.py`, `grading.py`, `attendance.py` | Many relational fields omit explicit `ondelete`, so default database behavior may not match business expectations. | Deleting master records can be blocked or leave unwanted references depending on defaults. | Define `ondelete` intentionally for financial, academic, and personal-data relationships. Prefer `restrict` for posted/approved business records. | Medium |
| R-11 | D | Medium | `../models/student.py`, `models/teacher.py`, `models/fee.py`, `models/payment.py`, `models/admission.py` | Unique business identifiers such as student email, teacher email, admission reference, fee invoice reference, and receipt reference rely mostly on code/sequence behavior, not always database-level uniqueness. | Duplicate business records can appear after imports or concurrent operations. | Add SQL/UniqueIndex constraints where the identifier must be unique; provide migrations for existing duplicates. | Medium |
| R-12 | E | Medium | Many Python files, examples: `../models/admission.py`, `models/enrollment.py`, `models/assignment.py`, `models/grading.py` | Some `ValidationError` messages are raw strings instead of `_()` translated strings. | The module is harder to translate and inconsistent with Odoo conventions. | Wrap user-visible server messages in `_()`. | Small |
| R-13 | C | Low | `models/enrollment.py:260-274` | Capacity checking uses safe parameterized SQL with `FOR UPDATE`, but still loops over sections and calls `search_count` per section. | Bulk enrollment into many sections can become slower than necessary. | Keep the row lock, but batch current counts using `_read_group`. | Medium |
| R-14 | E | Low | `../security/record_rules.xml` | The record rule file has large blank gaps and duplicate conceptual sections, making review difficult. | Security changes become harder and riskier to audit. | Split rules by role or clean the file structure after deduplicating XML IDs. | Small |

## Upgrade Plan

### Must Fix Now

1. Replace hard-coded default passwords.
   - Files: `../models/student.py`, `models/teacher.py`, `wizard/teacher_account_wizard.py` if it provisions users.
   - Migration needed: no.
   - Tests: create user, reset password, unauthorized reset, no password shown in notification.

2. Add teacher-scoped record rules for teaching models.
   - Files: `../security/record_rules.xml`, `tests/test_security_menus.py` or a new `tests/test_security_rules.py`.
   - Migration needed: no.
   - Scope: lesson plans, assignments, submissions, attendance, assessment results, service hours.

3. Deduplicate administrator record-rule XML IDs.
   - Files: `../security/record_rules.xml`.
   - Migration needed: no, unless existing XML IDs need to be renamed. Prefer merging records while keeping stable IDs.

4. Harden fee/payment/admission state machines.
   - Files: `../models/fee.py`, `models/payment.py`, `models/admission.py`, tests.
   - Migration needed: no.
   - Add explicit allowed transitions and double-click tests.

### Should Fix Next

1. Decide whether `admission.lead` and `admission.stage` are real features.
   - If yes: import models, load stage data and lead views, add ACLs/rules, connect menus.
   - If no: remove dead files and views from the module folder.

2. Add constraints for direct fee invoice lines and important business identifiers.
   - Files: `../models/fee.py`, `models/student.py`, `models/teacher.py`, `models/admission.py`, tests.
   - Migration needed: yes if constraints touch existing data that may contain duplicates or negative lines.

3. Lock approved academic records.
   - Files: `../models/grading.py`, related views, tests.
   - Migration needed: no.

4. Add explicit `ondelete` policies on important Many2one fields.
   - Files: finance, admissions, grading, attendance models.
   - Migration needed: usually no, unless database constraints must be recreated.

### Professional Polish

1. Wrap all server-visible messages in `_()`.
2. Replace high-volume `len(mapped(...))` count computations with grouped reads where needed.
3. Split or reorganize record rules by role once the current security behavior is tested.
4. Add indexes on fields used heavily in domains: state, student, program, semester, teacher, date, user link fields.
5. Extend test coverage for dashboard permission behavior and restricted-role UI actions.

## Proposed State Machines

Admission application:

- `draft -> submitted -> approved -> confirmed`
- `draft/submitted -> cancelled`
- `submitted -> rejected`
- `rejected/cancelled -> draft` only by admin
- Confirm only once; confirmation should be idempotent and should not regenerate extra fees.

Fee invoice:

- `draft -> posted`
- `posted -> paid` automatically when posted payments cover total
- `posted -> canceled` only when there are no posted payments
- `paid -> posted` automatically if a posted payment is canceled
- `posted/canceled -> draft` only by admin and only when no posted payments exist

Payment:

- `draft -> posted`
- `posted -> canceled`
- `canceled -> draft` only by admin/accounting role
- No edits after posted/canceled except allowed state action fields.

Assessment result:

- `draft -> published`
- `published -> draft` only by admin/HOD/dean, with chatter note
- Published grades should be read-only to ordinary teachers/students.

Report card/transcript:

- `draft -> generated -> approved`
- Regeneration only in `draft` or `generated`
- Approved records are locked except admin reset.

## Changes Made

Only this report was added:

- `SCAN_REPORT.md`

No model, view, security, or migration code was changed during this scan.

## Test Results

Static checks performed:

- Read manifest, security groups, ACLs, record rules, model files, key views, and key business-flow files.
- Extracted model inventory from Python AST.
- Searched for `sudo()`, raw SQL, state actions, constraints, indexes, record rules, and XML IDs.
- Confirmed `admission.lead` and `admission.stage` have no ACL and are not imported by `../models/__init__.py`.
- Confirmed duplicate admin rule XML IDs in `../security/record_rules.xml`.

Runtime tests not run in this phase:

- `odoo-bin -d odoo -u school_management --stop-after-init`
- `odoo-bin -d <testdb> -i school_management --test-enable --stop-after-init`

The previous server-start issue caused by stray core edits in `../../../odoo/orm/models.py` has already been restored separately, and the registry loaded after that restore.

## Remaining Risks

- This is a source-code scan, not a full production-data audit. Existing duplicate emails, negative lines, or malformed states must be checked against the database before adding strict SQL constraints.
- Security rule changes should be tested with separate admin, teacher, HOD, dean, student, and portal users.
- Finance currently uses custom fee/payment models rather than Odoo Accounting documents. That can be acceptable for a school ledger, but it should be a deliberate decision if real accounting/legal invoices are required.
- Dashboard and frontend behavior should be smoke-tested in the browser after any security or state-machine changes, especially for restricted roles.
