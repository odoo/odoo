# University Management System
#
# Codebase-aligned model map as of 2026-09-10.
# "*" = implemented in the current addon
# "+" = planned / not yet implemented
# "ext" = extension of an existing Odoo model
# "wiz" = transient model wizard

# Dashboard
#     school.dashboard                              *
#     dashboard_shell / student_dashboard_shell / teacher_dashboard_shell  * (OWL shells)

# Structure
#     university.faculty                            *
#     university.department                         *
#     university.program                            *
#     university.subject                            *
#     university.classroom                          *

# Academic calendar
#     university.academic.year                      *
#     university.semester                           *
#     university.semester.subject                   *

# People
#     university.teacher                            *
#     university.student                            *
#     university.admission.application              *
#     res.users                                     ext -> adds teacher_id

# Delivery and registration
#     university.class.section                      *
#     university.enrollment                         *
#     university.academic.assignment                *
#     university.student.enrollment.wizard          wiz
#     university.bulk.enrollment.wizard             wiz
#     university.populate.class.wizard              wiz

# Teacher portal / academic work
#     university.lesson.plan                        *
#     university.assignment                         *
#     university.assignment.submission              *
#     university.timeslot                           *
#     university.timetable.slot                     *
#     university.timetable.generation.wizard        wiz
#     university.attendance                         *
#     university.notice.board                       *
#     university.service.hour                       *

# Grading and results
#     university.grade.scale                        *
#     university.grade.scale.line                   *
#     university.assessment.category                *
#     university.assessment.result                  *
#     university.report.card                        *
#     university.report.card.line                   *
#     university.transcript                         *
#     university.transcript.line                    *

# Finance
#     university.fee                                *
#     university.fee.line                           *
#     university.fee.structure                      *
#     university.fee.structure.line                 *
#     university.payment                            *

# Miscellaneous
#     university.capability                         *
#     university.document.signature                 *
#     university.teacher.account.wizard             wiz

# Planned models
#     university.schedule                           +
#     university.exam                               +
#     university.scholarship                        +
#     university.graduation                         +
#     university.certificate                        +
#   (student portal pages - views/portal_templates.xml is a placeholder)

# Security groups (res.groups.privilege "University Management")
#     group_school_user               School User (implies base.group_user)
#     group_school_student            Student (implies group_school_user)
#     group_school_teacher            Teacher (implies group_school_user)
#     group_school_hod                Head of Department (implies group_school_teacher)
#     group_school_dean               Head of Faculty (implies group_school_hod)
#     group_school_registrar          Registrar (implies group_school_user)
#     group_school_admin              University Administrator (implies dean, registrar,
#                                     teacher workspace, and base.group_system)
#     group_teacher_dashboard         Teacher dashboard support group
#                                     (implies group_school_teacher)
#     group_student_portal            Student Portal (implies base.group_portal;
#                                     external role, no backend access)
#
# Functional dashboard roles: Student, Teacher/Advisor, Head of Department,
# Head of Faculty, Registrar, University Administrator.

# Security flow reference
#     res.users.teacher_id -> university.teacher
#     university.teacher -> department
#     department -> faculty
#     record rules scope data through that chain

# Data integrity
#     data/fix_user_teacher_links.xml       runs _fix_demo_staff_links() on -u
#     security/fix_demo_staff_links.sql     standalone SQL equivalent (reference)
#     migrations/19.0.1.2.0/pre-migrate.py
#     migrations/19.0.1.2.1/pre-migrate.py  student placement / dean-head / student id

# Maintenance scripts
#     scripts/fix_empty_assignment_teachers.py       * (re-links assignments with empty teacher_id)
#     scripts/cleanup_student_data.py                *
#     scripts/cleanup_teacher_data.py                *
