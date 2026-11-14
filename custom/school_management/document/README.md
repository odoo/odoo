# School Management Documentation

This folder contains the technical and project documentation for the custom Odoo addon `school_management`.

## Documentation map

- [project_overview.md](./project_overview.md) — high-level architecture, domain model, security, and implementation notes.
- [project_structure.md.md](./project_structure.md.md) — codebase-aligned model and structure inventory for the addon.
- [student_dashboard_shell.md](./student_dashboard_shell.md) — detailed technical specification for the student dashboard shell.
- [student_role_features.md](./student_role_features.md) — student permissions, features, and role behavior.
- [Grading_Benchmark_Research.md](./Grading_Benchmark_Research.md) — grading benchmark and academic policy research.
- [Grading_GPA_Policy.md](./Grading_GPA_Policy.md) — GPA and grade policy notes.
- [Quiz_Deadline_Session_Rules.md](./Quiz_Deadline_Session_Rules.md) — quiz and session deadline rules.
- [Transcript_Risk_Integration.md](./Transcript_Risk_Integration.md) — transcript risk and integration notes.
- [Student_Analytics_Advisor_Dashboard_BRD_SRS.md](./Student_Analytics_Advisor_Dashboard_BRD_SRS.md) — advisor dashboard requirements.
- [Exam_Module_BRD_SRS.md](./Exam_Module_BRD_SRS.md) — exam module business requirements and system design.
- [SCHOOL_MANAGEMENT_QNA_REVIEW_9b9dd9a6.md](./SCHOOL_MANAGEMENT_QNA_REVIEW_9b9dd9a6.md) — review and QA notes.
- [university_management_system_architecture.md](./university_management_system_architecture.md) — broader architectural context.
- [agent_guide.md](./agent_guide.md) — operational guidance for automated assistants.
- [local_configuration_guide.md](./local_configuration_guide.md) — local Odoo configuration help.
- [login_guide.md](./login_guide.md) — login and access guidance.

## Recommended reading order

1. Start with [project_overview.md](./project_overview.md) to understand module scope and architecture.
2. Review [project_structure.md.md](./project_structure.md.md) to map models, views, and security.
3. Read [student_dashboard_shell.md](./student_dashboard_shell.md) for the frontend implementation details.
4. Use the domain-specific documents for grading, transcripts, admissions, and exam workflows.

## Custom module alignment

These documents are scoped to the custom addon under `custom/school_management`, and should be read alongside the actual Odoo module files in `models/`, `views/`, `security/`, `static/`, and `reports/`.
