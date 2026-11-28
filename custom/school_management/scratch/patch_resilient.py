with open("static/src/school_management/teacher_dashboard_shell.js", "r", encoding="utf-8") as f:
    c = f.read()

# 1. KPI counts
old_kpi = """                const [totalClasses, totalAssignments, pendingSubmissionsCount, pendingServiceHours, adviseeCount, highRiskAdvisees] = await Promise.all([
                    this.orm.searchCount("university.timetable.slot", [["teacher_id", "=", teacherId]]),
                    this.orm.searchCount("university.assignment", [["teacher_id", "=", teacherId]]),
                    this.orm.searchCount("university.assignment.submission", [
                        ["assignment_id.teacher_id", "=", teacherId],
                        ["state", "=", "submitted"],
                    ]),
                    this.orm.searchCount("university.service.hour", [
                        ["teacher_id", "=", teacherId],
                        ["state", "=", "pending"],
                    ]),
                    this.orm.searchCount("university.student", [["advisor_id", "=", teacherId]]),
                    this.orm.searchCount("university.student", [["advisor_id", "=", teacherId], ["risk_level", "=", "high"]]),
                ]);"""

new_kpi = """                const [totalClasses, totalAssignments, pendingSubmissionsCount, pendingServiceHours, adviseeCount, highRiskAdvisees] = await Promise.all([
                    this.orm.searchCount("university.timetable.slot", [["teacher_id", "=", teacherId]]).catch(() => 0),
                    this.orm.searchCount("university.assignment", [["teacher_id", "=", teacherId]]).catch(() => 0),
                    this.orm.searchCount("university.assignment.submission", [
                        ["assignment_id.teacher_id", "=", teacherId],
                        ["state", "=", "submitted"],
                    ]).catch(() => 0),
                    this.orm.searchCount("university.service.hour", [
                        ["teacher_id", "=", teacherId],
                        ["state", "=", "pending"],
                    ]).catch(() => 0),
                    this.orm.searchCount("university.student", [["advisor_id", "=", teacherId]]).catch(() => 0),
                    this.orm.searchCount("university.student", [["advisor_id", "=", teacherId], ["risk_level", "=", "high"]]).catch(() => 0),
                ]);"""

assert old_kpi in c, "old_kpi not found"
c = c.replace(old_kpi, new_kpi, 1)

# 2. Pending Submissions & Teacher Assignments
old_subs = """                // 4. Fetch Pending Submissions for quick review
                this.state.pendingSubmissions = await this.orm.searchRead(
                    "university.assignment.submission",
                    [
                        ["assignment_id.teacher_id", "=", teacherId],
                        ["state", "=", "submitted"],
                    ],
                    ["name", "assignment_id", "student_id", "create_date", "state"],
                    { limit: 10, order: "create_date desc" }
                );

                // 5. Fetch Teacher's Published Assignments
                this.state.teacherAssignments = await this.orm.searchRead(
                    "university.assignment",
                    [["teacher_id", "=", teacherId]],
                    ["name", "subject_id", "section_id", "due_date", "max_score", "state", "submission_count"],
                    { limit: 10, order: "create_date desc" }
                );"""

new_subs = """                // 4. Fetch Pending Submissions for quick review
                try {
                    this.state.pendingSubmissions = await this.orm.searchRead(
                        "university.assignment.submission",
                        [
                            ["assignment_id.teacher_id", "=", teacherId],
                            ["state", "=", "submitted"],
                        ],
                        ["name", "assignment_id", "student_id", "create_date", "state"],
                        { limit: 10, order: "create_date desc" }
                    );
                } catch {
                    this.state.pendingSubmissions = [];
                }

                // 5. Fetch Teacher's Published Assignments
                try {
                    this.state.teacherAssignments = await this.orm.searchRead(
                        "university.assignment",
                        [["teacher_id", "=", teacherId]],
                        ["name", "subject_id", "section_id", "due_date", "max_score", "state", "submission_count"],
                        { limit: 10, order: "create_date desc" }
                    );
                } catch {
                    this.state.teacherAssignments = [];
                }"""

assert old_subs in c, "old_subs not found"
c = c.replace(old_subs, new_subs, 1)

# 3. Lesson plans and advisees
old_plans = """                // 7. Fetch Lesson Plans
                this.state.lessonPlans = await this.orm.searchRead(
                    "university.lesson.plan",
                    [["teacher_id", "=", teacherId]],
                    ["name", "subject_id", "create_date"],
                    { limit: 10, order: "create_date desc" }
                );

                // 8. Fetch Advisees & Follow-ups
                const [advisees, followups] = await Promise.all([
                    this.orm.searchRead(
                        "university.student",
                        [["advisor_id", "=", teacherId]],
                        ["name", "student_id", "gpa", "attendance_rate", "risk_level", "risk_reason", "current_semester_id"],
                        { limit: 20, order: "risk_level desc, gpa asc" }
                    ),
                    this.orm.searchRead(
                        "university.student.followup",
                        [["advisor_id", "=", teacherId], ["state", "in", ["pending", "in_progress"]]],
                        ["title", "student_id", "action_type", "date_deadline", "state", "description"],
                        { limit: 10, order: "date_deadline asc" }
                    ),
                ]);
                this.state.advisees = advisees;
                this.state.followups = followups;"""

new_plans = """                // 7. Fetch Lesson Plans
                try {
                    this.state.lessonPlans = await this.orm.searchRead(
                        "university.lesson.plan",
                        [["teacher_id", "=", teacherId]],
                        ["name", "subject_id", "create_date"],
                        { limit: 10, order: "create_date desc" }
                    );
                } catch {
                    this.state.lessonPlans = [];
                }

                // 8. Fetch Advisees & Follow-ups
                try {
                    const [advisees, followups] = await Promise.all([
                        this.orm.searchRead(
                            "university.student",
                            [["advisor_id", "=", teacherId]],
                            ["name", "student_id", "gpa", "attendance_rate", "risk_level", "risk_reason", "current_semester_id"],
                            { limit: 20, order: "risk_level desc, gpa asc" }
                        ).catch(() => []),
                        this.orm.searchRead(
                            "university.student.followup",
                            [["advisor_id", "=", teacherId], ["state", "in", ["pending", "in_progress"]]],
                            ["title", "student_id", "action_type", "date_deadline", "state", "description"],
                            { limit: 10, order: "date_deadline asc" }
                        ).catch(() => []),
                    ]);
                    this.state.advisees = advisees || [];
                    this.state.followups = followups || [];
                } catch {
                    this.state.advisees = [];
                    this.state.followups = [];
                }"""

assert old_plans in c, "old_plans not found"
c = c.replace(old_plans, new_plans, 1)

# 4. Attendance counts
old_att = """                // 9. Fetch Attendance stats
                const [presentCount, absentCount, lateCount, excusedCount] = await Promise.all([
                    this.orm.searchCount("university.attendance", [["teacher_id", "=", teacherId], ["status", "=", "present"]]),
                    this.orm.searchCount("university.attendance", [["teacher_id", "=", teacherId], ["status", "=", "absent"]]),
                    this.orm.searchCount("university.attendance", [["teacher_id", "=", teacherId], ["status", "=", "late"]]),
                    this.orm.searchCount("university.attendance", [["teacher_id", "=", teacherId], ["status", "=", "excused"]]),
                ]);"""

new_att = """                // 9. Fetch Attendance stats
                const [presentCount, absentCount, lateCount, excusedCount] = await Promise.all([
                    this.orm.searchCount("university.attendance", [["teacher_id", "=", teacherId], ["status", "=", "present"]]).catch(() => 0),
                    this.orm.searchCount("university.attendance", [["teacher_id", "=", teacherId], ["status", "=", "absent"]]).catch(() => 0),
                    this.orm.searchCount("university.attendance", [["teacher_id", "=", teacherId], ["status", "=", "late"]]).catch(() => 0),
                    this.orm.searchCount("university.attendance", [["teacher_id", "=", teacherId], ["status", "=", "excused"]]).catch(() => 0),
                ]);"""

assert old_att in c, "old_att not found"
c = c.replace(old_att, new_att, 1)

with open("static/src/school_management/teacher_dashboard_shell.js", "w", encoding="utf-8") as f:
    f.write(c)

print("Applied robust resilience to all queries in teacher_dashboard_shell.js!")
