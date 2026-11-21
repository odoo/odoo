import re

with open("static/src/school_management/teacher_dashboard_shell.xml", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace TAB 6: EXAMS & MARKSHEETS block
tab6_start = "<!-- TAB 6: EXAMS & MARKSHEETS -->"
tab6_end = "<!-- Bottom Quick Links Bar -->"

start_idx = content.find(tab6_start)
end_idx = content.find(tab6_end)

if start_idx == -1 or end_idx == -1:
    print(f"Error: tab6 block not found. start: {start_idx}, end: {end_idx}")
    exit(1)

new_tab6 = """<!-- TAB 6: EXAMS & MARKSHEETS -->
                            <div t-if="state.activeTab === 'exams'">
                                <!-- Hub Header -->
                                <div class="d-flex flex-wrap align-items-center justify-content-between mb-4 gap-2 border-bottom pb-3">
                                    <div>
                                        <h3 class="h5 mb-1 text-dark fw-bold">
                                            <i class="fa fa-file-excel-o me-2 text-success"/>Course Examinations &amp; Marksheets
                                        </h3>
                                        <p class="text-muted small mb-0">
                                            Export official Harvard-styled Excel marksheets with precalculated formulas, input grades, and track class academic performance.
                                        </p>
                                    </div>
                                    <div class="d-flex gap-2">
                                        <button type="button" class="btn btn-outline-primary btn-sm"
                                                t-on-click="() => this.openAllExams()">
                                            <i class="fa fa-external-link me-1"/>Manage All Exams
                                        </button>
                                    </div>
                                </div>

                                <!-- 4-Column Exam Performance Analytics KPI Cards -->
                                <div class="row g-3 mb-4">
                                    <div class="col-6 col-md-3">
                                        <div class="p-3 bg-white rounded-3 border text-center h-100 shadow-2xs o_exam_kpi_card">
                                            <div class="text-muted very-small fw-bold text-uppercase tracking-wider">Total Examinations</div>
                                            <div class="fs-3 fw-bold text-dark mt-1" t-esc="state.examStats.total"/>
                                            <div class="very-small text-muted">Assigned Tests &amp; Finals</div>
                                        </div>
                                    </div>
                                    <div class="col-6 col-md-3">
                                        <div class="p-3 bg-white rounded-3 border text-center h-100 shadow-2xs o_exam_kpi_card border-start border-3 border-success">
                                            <div class="text-success very-small fw-bold text-uppercase tracking-wider">Completed &amp; Published</div>
                                            <div class="fs-3 fw-bold text-success mt-1" t-esc="state.examStats.completed"/>
                                            <div class="very-small text-muted">Scores Finalized</div>
                                        </div>
                                    </div>
                                    <div class="col-6 col-md-3">
                                        <div class="p-3 bg-white rounded-3 border text-center h-100 shadow-2xs o_exam_kpi_card border-start border-3 border-warning">
                                            <div class="text-warning very-small fw-bold text-uppercase tracking-wider">Pending Grading</div>
                                            <div class="fs-3 fw-bold text-warning mt-1" t-esc="state.examStats.pending"/>
                                            <div class="very-small text-muted">Awaiting Evaluation</div>
                                        </div>
                                    </div>
                                    <div class="col-6 col-md-3">
                                        <div class="p-3 bg-white rounded-3 border text-center h-100 shadow-2xs o_exam_kpi_card border-start border-3 border-primary">
                                            <div class="text-primary very-small fw-bold text-uppercase tracking-wider">Cohort Pass Rate</div>
                                            <div class="fs-3 fw-bold text-primary mt-1" t-esc="state.examStats.avgPassRate + '%'"/>
                                            <div class="very-small text-muted">Class Average</div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Filter & Search Toolbar -->
                                <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-3 p-3 bg-light rounded-3 border">
                                    <!-- Exam Type Filter Pills -->
                                    <div class="d-flex flex-wrap align-items-center gap-1">
                                        <span class="very-small text-muted fw-bold me-1 text-uppercase">Type:</span>
                                        <button type="button"
                                                t-att-class="'btn btn-sm py-1 px-2 ' + (state.examFilterType === 'all' ? 'btn-primary' : 'btn-outline-secondary bg-white')"
                                                t-on-click="() => this.setExamFilterType('all')">
                                            All Types
                                        </button>
                                        <button type="button"
                                                t-att-class="'btn btn-sm py-1 px-2 ' + (state.examFilterType === 'quiz' ? 'btn-primary' : 'btn-outline-secondary bg-white')"
                                                t-on-click="() => this.setExamFilterType('quiz')">
                                            Quiz
                                        </button>
                                        <button type="button"
                                                t-att-class="'btn btn-sm py-1 px-2 ' + (state.examFilterType === 'midterm' ? 'btn-primary' : 'btn-outline-secondary bg-white')"
                                                t-on-click="() => this.setExamFilterType('midterm')">
                                            Midterm
                                        </button>
                                        <button type="button"
                                                t-att-class="'btn btn-sm py-1 px-2 ' + (state.examFilterType === 'final' ? 'btn-primary' : 'btn-outline-secondary bg-white')"
                                                t-on-click="() => this.setExamFilterType('final')">
                                            Final Exam
                                        </button>
                                    </div>

                                    <!-- Status Select and Search Box -->
                                    <div class="d-flex flex-wrap align-items-center gap-2">
                                        <select class="form-select form-select-sm shadow-none" style="width: auto; min-width: 140px;"
                                                t-att-value="state.examFilterState"
                                                t-on-change="(ev) => this.setExamFilterState(ev.target.value)">
                                            <option value="all">All Statuses</option>
                                            <option value="draft">Draft</option>
                                            <option value="scheduled">Scheduled</option>
                                            <option value="ongoing">Ongoing</option>
                                            <option value="pending">Pending Grading</option>
                                            <option value="completed">Completed &amp; Published</option>
                                        </select>

                                        <div class="input-group input-group-sm" style="width: 220px;">
                                            <span class="input-group-text bg-white border-end-0 text-muted"><i class="fa fa-search"/></span>
                                            <input type="text" class="form-control form-control-sm border-start-0 ps-0 shadow-none"
                                                   placeholder="Search course or exam..."
                                                   t-att-value="state.examSearchQuery"
                                                   t-on-input="(ev) => this.onExamSearch(ev)"/>
                                            <button t-if="state.examSearchQuery" type="button" class="btn btn-outline-secondary border-start-0"
                                                    t-on-click="() => { this.state.examSearchQuery = ''; }">
                                                <i class="fa fa-times"/>
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <!-- Exam Table / Results -->
                                <t t-if="this.filteredExams and this.filteredExams.length">
                                    <div class="table-responsive rounded-3 border bg-white mb-2">
                                        <table class="table table-hover align-middle mb-0">
                                            <thead class="table-light">
                                                <tr>
                                                    <th>Exam &amp; Subject</th>
                                                    <th>Section &amp; Schedule</th>
                                                    <th>Weight &amp; Points</th>
                                                    <th style="min-width: 140px;">Grading Progress</th>
                                                    <th>Pass Rate</th>
                                                    <th>Status</th>
                                                    <th class="text-end pe-3">Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr t-foreach="this.filteredExams" t-as="exam" t-key="exam.id">
                                                    <td>
                                                        <div class="d-flex align-items-start gap-2">
                                                            <div class="mt-1">
                                                                <i t-if="exam.exam_type === 'final'" class="fa fa-graduation-cap text-danger" title="Final Exam"/>
                                                                <i t-elif="exam.exam_type === 'midterm'" class="fa fa-bookmark text-primary" title="Midterm Exam"/>
                                                                <i t-elif="exam.exam_type === 'quiz'" class="fa fa-check-square-o text-warning" title="Quiz"/>
                                                                <i t-else="" class="fa fa-file-text-o text-secondary"/>
                                                            </div>
                                                            <div>
                                                                <a href="javascript:void(0)" class="text-decoration-none fw-bold text-primary d-block lh-sm"
                                                                   t-on-click="() => this.openExam(exam.id)" t-esc="exam.name"/>
                                                                <div class="text-dark small fw-semibold mt-1" t-esc="exam.subject_id ? exam.subject_id[1] : 'Subject'"/>
                                                                <div class="very-small text-muted" t-if="exam.department_id">
                                                                    <span t-esc="exam.department_id[1]"/>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <div class="d-flex flex-column gap-1">
                                                            <span class="badge bg-light text-dark border align-self-start" t-esc="exam.section_id ? exam.section_id[1] : 'All Sections'"/>
                                                            <div class="very-small text-muted">
                                                                <i class="fa fa-calendar-o me-1 text-primary"/>
                                                                <span t-esc="exam.dateFormatted || exam.exam_date || 'Date TBA'"/>
                                                            </div>
                                                            <div class="very-small text-muted" t-if="exam.duration_minutes">
                                                                <i class="fa fa-clock-o me-1 text-muted"/>
                                                                <span t-esc="exam.duration_minutes + ' mins'"/>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <div class="fw-bold text-dark" t-esc="(exam.max_score || 100) + ' pts'"/>
                                                        <div class="very-small text-muted" t-if="exam.weight_percent">
                                                            Weight: <strong t-esc="exam.weight_percent + '%'"/>
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <div class="d-flex align-items-center justify-content-between very-small mb-1">
                                                            <span class="fw-semibold text-muted">
                                                                <t t-esc="exam.scored_count || 0"/> / <t t-esc="exam.student_count || 0"/>
                                                            </span>
                                                            <span class="fw-bold" t-att-class="exam.progressPct === 100 ? 'text-success' : 'text-primary'">
                                                                <t t-esc="exam.progressPct + '%'"/>
                                                            </span>
                                                        </div>
                                                        <div class="progress" style="height: 6px;">
                                                            <div class="progress-bar" role="progressbar"
                                                                 t-att-style="'width: ' + exam.progressPct + '%;'"
                                                                 t-att-class="exam.progressPct === 100 ? 'bg-success' : 'bg-primary'"/>
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <t t-if="exam.scored_count">
                                                            <span t-att-class="'badge ' + (exam.passRate >= 75 ? 'bg-success-subtle text-success border border-success-subtle' : (exam.passRate >= 50 ? 'bg-warning-subtle text-warning border border-warning-subtle' : 'bg-danger-subtle text-danger border border-danger-subtle'))">
                                                                <t t-esc="exam.passRate + '% Pass'"/>
                                                            </span>
                                                            <div class="very-small text-muted mt-1" t-if="exam.average_score">
                                                                Avg: <strong t-esc="exam.average_score.toFixed(1)"/>
                                                            </div>
                                                        </t>
                                                        <t t-else="">
                                                            <span class="badge bg-light text-muted border">No Scores</span>
                                                        </t>
                                                    </td>
                                                    <td>
                                                        <span t-if="exam.state === 'draft'" class="badge bg-secondary-subtle text-secondary border">Draft</span>
                                                        <span t-elif="exam.state === 'scheduled'" class="badge bg-info-subtle text-info border">Scheduled</span>
                                                        <span t-elif="exam.state === 'ongoing'" class="badge bg-warning-subtle text-warning border">Ongoing</span>
                                                        <span t-elif="exam.state === 'grading'" class="badge bg-primary-subtle text-primary border">Grading</span>
                                                        <span t-elif="exam.state === 'published' or exam.state === 'completed'" class="badge bg-success-subtle text-success border">Published</span>
                                                        <span t-else="" class="badge bg-light text-dark border text-capitalize" t-esc="exam.state"/>
                                                    </td>
                                                    <td class="text-end pe-3">
                                                        <div class="d-flex align-items-center justify-content-end gap-1">
                                                            <button type="button" class="btn btn-outline-success btn-sm py-1 px-2 fw-semibold d-inline-flex align-items-center gap-1 shadow-2xs"
                                                                    t-on-click="() => this.downloadExamMarksheet(exam.id)"
                                                                    title="Export Harvard Official Excel Marksheet">
                                                                <i class="fa fa-file-excel-o text-success" aria-hidden="true"/>
                                                                <span>Marksheet</span>
                                                            </button>
                                                            <button type="button" class="btn btn-outline-primary btn-sm py-1 px-2 fw-semibold d-inline-flex align-items-center gap-1"
                                                                    t-on-click="() => this.openExamScores(exam.id)"
                                                                    title="Input and Review Student Scores">
                                                                <i class="fa fa-pencil" aria-hidden="true"/>
                                                                <span>Scores</span>
                                                            </button>
                                                            <button type="button" class="btn btn-outline-secondary btn-sm py-1 px-2"
                                                                    t-on-click="() => this.openExam(exam.id)"
                                                                    title="View Exam Form &amp; Settings">
                                                                <i class="fa fa-external-link" aria-hidden="true"/>
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </t>
                                <t t-else="">
                                    <div class="p-5 text-center bg-light rounded-3 border">
                                        <i class="fa fa-file-excel-o fa-3x text-muted mb-3 opacity-50"/>
                                        <h4 class="h6 text-dark mb-1 fw-bold">No Examinations Found</h4>
                                        <p class="text-muted small mb-3">
                                            <t t-if="state.exams and state.exams.length">
                                                No examinations match your current filter or search criteria.
                                            </t>
                                            <t t-else="">
                                                No course examinations are assigned to your teaching profile yet.
                                            </t>
                                        </p>
                                        <button t-if="state.exams and state.exams.length" type="button" class="btn btn-outline-primary btn-sm"
                                                t-on-click="() => this.resetExamFilters()">
                                            <i class="fa fa-refresh me-1"/>Reset Filters
                                        </button>
                                    </div>
                                </t>
                            </div>
                        </div>
                    </div>

                    """

content = content[:start_idx] + new_tab6 + content[end_idx:]

# 2. Add Quick Marksheets to Sidebar before Campus Notices
sidebar_target = '<!-- 3. Campus Notices & Announcements Feed Card -->'
sidebar_replacement = """<!-- 3. Quick Marksheet Exports Card -->
                <div class="o_sidebar_card">
                    <div class="d-flex align-items-center justify-content-between mb-3 pb-2 border-bottom">
                        <h4 class="h6 mb-0 fw-bold text-dark">
                            <i class="fa fa-file-excel-o text-success me-2" aria-hidden="true"/>Quick Marksheets
                        </h4>
                        <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none very-small"
                                t-on-click="() => this.setActiveTab('exams')">
                            All Exams &gt;
                        </button>
                    </div>
                    <t t-if="this.recentExamsForSidebar and this.recentExamsForSidebar.length">
                        <div class="d-flex flex-column gap-2">
                            <div t-foreach="this.recentExamsForSidebar" t-as="rexam" t-key="rexam.id"
                                 class="p-2 rounded-2 bg-light border d-flex align-items-center justify-content-between gap-2">
                                <div class="overflow-hidden">
                                    <div class="fw-semibold text-dark very-small text-truncate" t-esc="rexam.name"/>
                                    <div class="very-small text-muted text-truncate">
                                        <span t-esc="rexam.subject_id ? rexam.subject_id[1] : 'Subject'"/> •
                                        <span t-esc="rexam.section_id ? rexam.section_id[1] : 'Section'"/>
                                    </div>
                                </div>
                                <div class="d-flex align-items-center gap-1 flex-shrink-0">
                                    <button type="button" class="btn btn-sm btn-outline-success p-1 py-0 very-small"
                                            t-on-click="() => this.downloadExamMarksheet(rexam.id)"
                                            title="Export Excel Marksheet">
                                        <i class="fa fa-download"/>
                                    </button>
                                    <button type="button" class="btn btn-sm btn-outline-primary p-1 py-0 very-small"
                                            t-on-click="() => this.openExamScores(rexam.id)"
                                            title="Grade Scores">
                                        <i class="fa fa-pencil"/>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </t>
                    <t t-else="">
                        <div class="p-3 text-center bg-light rounded text-muted very-small">
                            <i class="fa fa-folder-open-o me-1"/> No course exams available.
                        </div>
                    </t>
                </div>

                <!-- 4. Campus Notices & Announcements Feed Card -->"""

if sidebar_target in content:
    content = content.replace(sidebar_target, sidebar_replacement, 1)
    print("Sidebar quick marksheets card injected.")
else:
    print("Warning: sidebar target not found!")

with open("static/src/school_management/teacher_dashboard_shell.xml", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated teacher_dashboard_shell.xml successfully!")
