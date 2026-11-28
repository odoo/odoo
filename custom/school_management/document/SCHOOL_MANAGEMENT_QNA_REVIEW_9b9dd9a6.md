# School Management Q&A — Review and Improvement Report

**Reviewed file:** `school_management_project_analysis_qna.docx`  
**Review date:** 2 September 2026  
**Document size:** 35 questions and answers, 10 main sections, and 3 tables

> **Important:** This is a review of the Word document. The complete Odoo addon source code was not supplied with this request, so code-specific statements are marked **Verify in source** rather than treated as confirmed defects.

## Codebase Status Update (2026-09-10)

This historical review was written against the Q&A document, not the codebase. The items below are now **verified in the current addon source** and change the review's findings:

| Review issue | Current codebase status |
|---|---|
| ISSUE-001 — broad `base.group_user` CRUD | **Resolved in source.** `security/ir.model.access.csv` grants are role-based (`school_management.group_school_user/student/teacher/hod/dean/admin` and portal). The only `base.group_user`-style rows reference `base.group_system` (standard Odoo superuser), and many sensitive models use `perm_unlink = 0` for non-admin roles. |
| ISSUE-002 — `security/security.xml` not loaded | **Resolved in source.** `__manifest__.py` loads `security/security.xml` as the first data entry. |
| ISSUE-003 — no record rules | **Resolved in source.** `security/record_rules.xml` is loaded and contains role-scoped rules (teacher sees own sections/subjects, HOD/dean scoped by department/faculty, student sees own profile/enrollments/fees/payments, portal users see own records read-only). |
| Odoo 19 compatibility (DOC-002) | **Verified.** Manifest is `version 19.0.1.2.1`, depends `auth_signup`, `base`, `mail`, `portal`, `web`; the addon upgrades with `-u school_management` on the local `odoo` database. |
| Security XML loading order | **Verified.** The manifest orders `security/security.xml`, `ir.model.access.csv`, then `record_rules.xml` before data/views. |
| Missing manifest entries (DOC-001 subset) | **Verified.** All manifest `data` entries resolve to existing files; `views/portal_templates.xml` exists as a placeholder. |
| Enrollment/attendance status | Attendance is now an implemented model (`university.attendance`, no dedicated view file yet) rather than "planned". |
| New since the review | Admission applications, capability, document signature, fee structures, grading/assessment/report card/transcript models, lesson plans, assignments/submissions, timetables, notice board, service hours, a Teacher Dashboard group/shell, and two student/portal roles (`group_school_student`, `group_student_portal`). |

Remaining open items from the review that are still valid: enrollment-capacity concurrency, finance edge cases (refunds, overpayments, integration with `account`), multi-company behavior, portal page templates (currently a placeholder), and automated tests beyond `test_payment.py`.

---

## 1. Overall Assessment

The document is clear, readable, and useful as a high-level project overview. It explains the principal models, enrollment flow, finance workflow, dashboard, reports, and known security concerns.

However, it is not yet strong enough to serve as a complete technical audit or final project-defense guide because:

- Many exact implementation claims do not include file, model, method, or test evidence.
- Serious security issues are described too softly.
- Enrollment capacity concurrency is not discussed.
- Finance controls, privacy, multi-company behavior, and audit requirements need more depth.
- No automated test results or installation evidence are provided.
- The roadmap has no acceptance criteria, owner, status, or target milestone.

### Review Verdict

| Area | Assessment |
|---|---|
| Project overview | Good |
| Model explanation | Good but needs an ER diagram |
| Wizard explanation | Useful but incomplete |
| Security analysis | Important findings, insufficient severity |
| Finance analysis | Basic; not production-ready |
| Testing evidence | Missing |
| Traceability to source | Missing |
| Project-defense readiness | Needs improvement |
| Document navigation | Needs TOC, metadata, headers, and page numbers |

## 2. Critical Project Issues Highlighted by the Document

### ISSUE-001 — Internal Users Apparently Receive Broad CRUD Access

- **Status:** Verify in source
- **Document statement:** Most business models grant full create, read, write, and delete access to `base.group_user`.
- **Why this is critical:** Every internal Odoo user may be able to change or delete student, enrollment, fee, and payment records.
- **Required improvement:**
  - Create separate groups such as School Administrator, Registrar, Teacher, Finance Officer, and Read-Only User.
  - Grant only the minimum required model permissions.
  - Remove delete permission from sensitive operational and financial records where possible.
  - Test permissions with real users in every group.
- **Acceptance criteria:** A teacher cannot edit payments; a finance officer cannot change academic structures; a regular internal user cannot delete students or posted financial records.

### ISSUE-002 — Custom Security Group Is Reportedly Not Loaded

- **Status:** Verify in source
- **Document statement:** `security/security.xml` defines School User, but the manifest does not load the file.
- **Risk:** The custom group may not exist after installation, making intended access-control design ineffective.
- **Required improvement:** Add the security XML before `ir.model.access.csv` in the manifest, or remove the unused file and redesign access explicitly.

```python
"data": [
    "security/security.xml",
    "security/ir.model.access.csv",
    # Remaining views and data files
]
```

- **Acceptance criteria:** Installing the module on a clean database creates every expected group and all access-control references resolve successfully.

### ISSUE-003 — No Record Rules Are Reported

- **Status:** Verify in source
- **Risk:** Model-level access alone does not limit which records a user can see. Teachers may see all students, and users may see all fees and payments.
- **Required improvement:** Add record rules based on role, department, assigned class sections, responsible user, and company where appropriate.
- **Acceptance criteria:** Security tests prove that users cannot access unauthorized records through forms, lists, searches, exports, RPC calls, or direct URLs.

### ISSUE-004 — Capacity Checks May Be Vulnerable to Concurrency

- **Status:** Missing analysis
- **Document statement:** Wizards check whether a class section is full before enrolling students.
- **Risk:** Two concurrent users can both pass a Python capacity check and overfill the same section.
- **Required improvement:** Use transaction-safe locking or another database-backed concurrency strategy around capacity validation and enrollment creation.
- **Acceptance criteria:** A concurrent test cannot create more active enrollments than the section capacity.

### ISSUE-005 — Student and Financial Data Need Explicit Privacy Controls

- **Status:** Missing analysis
- **Risk:** The models store identity, contact, emergency-contact, photo, fee, and payment data. Broad internal access could expose personal and financial information.
- **Required improvement:** Define data classification, minimum access, export restrictions, retention, deletion/anonymization, attachment security, and audit logging.
- **Acceptance criteria:** Each role has documented field and record visibility, and sensitive access is logged.

## 3. High-Priority Document Issues

### DOC-001 — Exact Claims Have No Source References

The document makes detailed statements about:

- Manifest dependencies and flags
- Model names and relationships
- SQL constraints
- Python constraints and methods
- Wizard validation
- Dashboard JavaScript behavior
- QWeb reports
- Missing manifest entries
- Duplicate imports
- A potentially incorrect payment domain

These claims should cite the relevant file and symbol.

**Recommended format:**

```text
Evidence: models/enrollment.py — university.enrollment,
constraint student_section_unique.
```

Line numbers or commit hashes should be added when the document is generated from a stable revision.

### DOC-002 — “Odoo 19” Compatibility Is Asserted Without Evidence

- **Problem:** The document calls the addon an Odoo 19 module but does not show the manifest version, installation result, server log, or compatibility test.
- **Improvement:** State the exact Odoo edition/build, Python version, PostgreSQL version, addon commit, and clean-install/upgrade result.
- **Better wording:** “The manifest targets Odoo 19; compatibility must be confirmed by a clean install and automated tests.”

### DOC-003 — “What Is Already Finished” Is Not Proven

- **Problem:** A file’s presence does not prove that the feature works correctly.
- **Improvement:** Label each capability as Implemented, Partially Implemented, Mocked, Planned, or Verified by Test.
- **Evidence to add:** Screenshot, menu path, model/method, automated test, expected result, and known limitation.

### DOC-004 — Security Findings Are Presented as Ordinary Recommendations

- **Problem:** Full CRUD access for `base.group_user`, an unloaded security file, and missing record rules are potentially release-blocking issues.
- **Improvement:** Give each finding a severity, impact, reproduction method, owner, status, and acceptance criteria.

### DOC-005 — The Two Enrollment Wizards Are Not Compared Clearly

- **Problem:** The document explains that two wizards exist but does not justify why both are necessary.
- **Improvement:** Add a comparison table covering launch location, target user, one-to-many direction, fields, validation, duplicate handling, capacity handling, return action, and access group.
- **Decision required:** Keep both when they represent distinct workflows; otherwise consolidate duplicated logic into shared model methods.

### DOC-006 — Duplicate Prevention Is Oversimplified

- **Problem:** `UNIQUE(student_id, section_id)` prevents identical rows but may also block valid re-enrollment after a cancelled record, depending on business requirements.
- **Improvement:** Define whether cancelled or withdrawn enrollments remain unique, are reactivated, or allow a new attempt with history.

### DOC-007 — Teacher Eligibility Rule Has an Ambiguous Fallback

- **Document statement:** If a subject has assigned teachers, the selected teacher must be one of them.
- **Question:** What happens when the subject has no assigned teachers?
- **Risk:** Any teacher may be allowed, or section creation may behave inconsistently.
- **Improvement:** Define and test the intended rule explicitly.

### DOC-008 — Finance Workflow Is Too Shallow

The report should discuss:

- Currency and rounding
- Partial payments
- Overpayments and credit balances
- Refunds and reversals
- Payment references and uniqueness
- Posting-date controls
- Period locking
- Editing posted records
- Audit trails
- Receipts and cancellation copies
- Reconciliation
- Integration with Odoo Accounting

The current text correctly states that the module is not full accounting, but it should clearly say that standalone balances must not be treated as an accounting ledger.

### DOC-009 — Payment and Invoice State Transitions Need a Diagram

Add explicit state diagrams such as:

```text
Fee: draft → posted → paid
       └────→ cancelled

Payment: draft → posted → cancelled/reversed
```

Each transition should list the allowed role, validation, side effects, reversibility, and audit record.

### DOC-010 — Multi-Company Behavior Is Missing

- **Problem:** Odoo installations frequently support multiple companies, but the document does not mention `company_id`, company-dependent sequences, currencies, record rules, or cross-company reporting.
- **Improvement:** State whether the module is single-company only. If multi-company is supported, document and test company isolation.

## 4. Technical Claims That Require Verification

The following should be checked directly in the addon before keeping them as facts:

| Claim | Verification Required |
|---|---|
| Manifest depends on `base`, `mail`, and `web` | Inspect `__manifest__.py`. |
| Module is compatible with Odoo 19 | Perform clean install and upgrade tests. |
| `student_section_unique` exists | Inspect `_sql_constraints` and database schema. |
| Teacher eligibility constraint works | Test allowed, disallowed, and empty teacher lists. |
| Wizards enforce capacity | Inspect both methods and run concurrency tests. |
| Only posted payments affect balances | Inspect dependencies and recomputation behavior. |
| Paid invoices recalculate after cancellation | Test cancellation and state rollback. |
| Dashboard values are accurate | Compare ORM results with database records. |
| Chart.js is loaded correctly | Inspect manifest assets and browser console. |
| Custom layout patch is safe | Test menus, dialogs, mobile layouts, upgrades, and other apps. |
| Two QWeb reports are installed | Verify report actions, templates, permissions, and PDF output. |
| Security XML is omitted from manifest | Inspect manifest loading order. |
| Duplicate dashboard import exists | Inspect `models/dashboard.py`. |
| Student payment action misses direct payments | Test the action domain against payments without fees. |

## 5. Specific Content Corrections

### Correction 1 — Rephrase the Scalability Claim

**Current idea:** The design is scalable because it uses sections.

**Improved answer:**

> The section-based model is extensible because it separates a subject definition from each scheduled offering. Scalability is not yet proven; it also depends on indexes, query counts, computed-field design, dashboard aggregation, concurrency handling, and load testing.

### Correction 2 — Strengthen the Security Answer

**Improved answer:**

> The reviewed document indicates that internal users may have broad CRUD access and that no record rules are present. If confirmed in source, this is a release-blocking authorization issue because student and financial records may be visible or editable by unauthorized staff. The module needs role-specific groups, least-privilege access rights, record rules, and automated security tests.

### Correction 3 — Clarify Enrollment Validation

**Improved answer:**

> The wizards appear to check selected students, duplicates, subject compatibility, and capacity. These application checks improve user feedback, but database uniqueness and transaction-safe capacity enforcement are still required to protect against concurrent enrollments.

### Correction 4 — Clarify Finance Readiness

**Improved answer:**

> The fee and payment models provide a lightweight operational billing workflow. They are not an accounting ledger and should not be represented as complete finance functionality until currency, refunds, reconciliation, audit controls, and optional `account` integration are implemented and tested.

### Correction 5 — Clarify “Finished” Features

Replace “finished” with one of these labels:

- **Implemented:** Source code exists.
- **Verified:** A repeatable test demonstrates correct behavior.
- **Partially implemented:** Main path exists but edge cases remain.
- **Planned:** No completed implementation evidence.
- **Known issue:** Implementation exists but has a confirmed defect.

## 6. Missing Questions to Add

Add at least the following questions and answers:

1. How does the module prevent concurrent over-enrollment?
2. What is the difference between an SQL constraint and a Python constraint?
3. Why are wizards implemented with `TransientModel`?
4. Who can launch each wizard?
5. What happens when a wizard partially fails?
6. How are withdrawn or cancelled enrollments handled?
7. How are schedule, teacher, classroom, and student conflicts detected?
8. How is student personal data protected?
9. How is multi-company isolation implemented?
10. Can posted fees or payments be edited or deleted?
11. How are refunds, reversals, and overpayments handled?
12. What currency and rounding rules are used?
13. How are sequences protected from duplication?
14. How does the dashboard avoid slow repeated count queries?
15. What happens if Chart.js fails to load?
16. How does the custom webclient patch affect other installed Odoo apps?
17. What automated tests currently pass?
18. How is the module installed on a clean Odoo database?
19. How is an older database upgraded to a new module version?
20. What logs and audit records help investigate a problem?

## 7. Missing Project Evidence

The improved document should include or link to:

- System context diagram
- Entity-relationship diagram
- Model relationship table with cardinalities
- User role and permission matrix
- Enrollment wizard sequence diagram
- Fee/payment state diagram
- Menu and action map
- Report list with screenshots
- Manifest data and asset loading order
- Installation and upgrade commands
- Automated test report
- Known bugs with reproduction steps
- Supported Odoo/Python/PostgreSQL versions
- Git commit or release version reviewed

## 8. Document Presentation Improvements

### PRESENTATION-001 — Document Metadata Is Generic

- Core title is `Word Document`, with no subject or author.
- Set a meaningful title, subject, author, keywords, version, and review date.

### PRESENTATION-002 — No Header, Footer, or Page Numbers

- Add project name and document version in the header.
- Add page numbers and confidentiality/status text in the footer.

### PRESENTATION-003 — No Table of Contents

- Add an automatic table of contents.
- Ensure question styles use outline levels or group questions under numbered subsections.

### PRESENTATION-004 — Questions Are Not Numbered by Section

- Prefer identifiers such as `ARCH-01`, `SEC-03`, and `FIN-05`.
- Stable identifiers make review comments and issue tracking easier.

### PRESENTATION-005 — Tables Need Descriptive Headers

- The extracted tables show blank generic columns before their real header row.
- Rebuild each table with a real header row and repeat it across pages.

### PRESENTATION-006 — No Change History

Add a revision table:

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-09-02 | Project team | Initial analysis |
| 1.1 | TBD | Project team | Security and evidence improvements |

## 9. Recommended Issue Template

Use this structure for every confirmed project bug:

```markdown
### BUG-XXX — Short Title

- Severity:
- Status:
- Affected version:
- File/model/method:
- Preconditions:
- Steps to reproduce:
- Expected result:
- Actual result:
- Business impact:
- Root cause:
- Proposed fix:
- Test cases:
- Acceptance criteria:
```

## 10. Recommended Improvement Roadmap

### Phase 1 — Security and Correctness

- Verify and repair manifest security loading.
- Replace broad `base.group_user` access with role-specific groups.
- Add record rules and security tests.
- Make capacity enforcement concurrency-safe.
- Fix the student-payment action domain if the reported issue is confirmed.

### Phase 2 — Finance and Data Governance

- Define currencies, rounding, refunds, overpayments, and reconciliation.
- Protect posted records and add audit trails.
- Define privacy, retention, exports, and multi-company behavior.

### Phase 3 — Quality Evidence

- Add model, wizard, security, finance, dashboard, and report tests.
- Record clean-install and upgrade results.
- Add source references and implementation-status labels to every answer.

### Phase 4 — Document and UX Quality

- Add diagrams, screenshots, TOC, metadata, page numbers, and revision history.
- Test dashboard performance and custom layout compatibility.
- Expand the guide with the missing questions listed above.

## 11. Definition of Done for the Revised Q&A

The revised document is ready when:

- Every implementation claim has a source reference or test result.
- Critical security findings are clearly labeled and resolved or tracked.
- Enrollment concurrency and financial edge cases are explained.
- Role, record-rule, and model-access matrices are included.
- The guide distinguishes implemented, verified, partial, planned, and known-issue features.
- Installation, upgrade, and automated test evidence are included.
- The Word file has correct metadata, TOC, headers, footers, and page numbers.
- All tables and diagrams are readable and named.

## 12. Final Recommendation

Do not rewrite the document from zero. Keep its current question-and-answer structure, but strengthen it with source evidence, severity, reproducible tests, concurrency analysis, finance controls, and security ownership. The most urgent project work is access control and record rules, followed by enrollment concurrency and finance correctness.

