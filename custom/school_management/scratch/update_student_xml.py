import xml.etree.ElementTree as ET

with open('static/src/school_management/student_dashboard_shell.xml', 'r', encoding='utf-8') as f:
    c = f.read()

target_start = """            <t t-else="">

                                <!-- ==================== DASHBOARD VIEW (when activeTab === 'dashboard') ==================== -->
                <t t-if="state.activeTab === 'dashboard'">
                    <div class="o_student_mockup_dashboard p-4">
                        <!-- Top Header Greeting -->
                        <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                            <div>
                                <h1 class="h3 fw-bold text-dark mb-1" t-esc="this.greeting"/>
                                <div class="d-flex align-items-center gap-2 text-muted small">
                                    <span>ID <t t-esc="this.studentIdDisplay"/></span>
                                    <span>&#8226;</span>
                                    <span t-esc="this.programDisplay"/>
                                    <span>&#8226;</span>
                                    <span class="badge o_badge_active_status text-capitalize" t-esc="state.student.status || 'Active'"/>
                                </div>
                            </div>
                            <div class="d-flex align-items-center gap-2">
                                <button type="button" class="btn btn-outline-secondary btn-sm fw-semibold o_btn_curriculum_pdf shadow-sm"
                                        t-on-click="() => this.printCurriculum()">
                                    Curriculum PDF
                                </button>
                                <button type="button" class="btn btn-primary btn-sm fw-semibold o_btn_request_transcript shadow-sm"
                                        t-on-click="() => this.openNewTranscriptRequest()">
                                    Request transcript
                                </button>
                            </div>
                        </div>

                        <!-- Alert Banners Row (Side-by-side 2 Columns) -->
                        <div class="row g-3 mb-4">
                            <!-- Banner 1: Attendance Warning -->
                            <div class="col-12 col-lg-6">
                                <div class="o_alert_card o_alert_attendance_card d-flex align-items-center justify-content-between p-3 rounded-3">
                                    <div class="d-flex align-items-center gap-3">
                                        <div class="o_alert_icon_circle o_alert_icon_red d-flex align-items-center justify-content-center">
                                            <i class="fa fa-exclamation"/>
                                        </div>
                                        <div>
                                            <div class="fw-bold text-dark o_alert_title">
                                                Attendance is <t t-esc="state.attendanceStats.rate || 62"/>%, below the 75% minimum
                                            </div>
                                            <div class="text-muted small">You're at risk of losing exam eligibility.</div>
                                        </div>
                                    </div>
                                    <button type="button" class="btn btn-outline-secondary btn-sm bg-white fw-semibold o_alert_btn"
                                            t-on-click="() => this.setActiveTab('attendance')">
                                        Submit excuse
                                    </button>
                                </div>
                            </div>

                            <!-- Banner 2: Tuition Overdue -->
                            <div class="col-12 col-lg-6">
                                <div class="o_alert_card o_alert_tuition_card d-flex align-items-center justify-content-between p-3 rounded-3">
                                    <div class="d-flex align-items-center gap-3">
                                        <div class="o_alert_icon_circle o_alert_icon_amber d-flex align-items-center justify-content-center">
                                            <i class="fa fa-dollar"/>
                                        </div>
                                        <div>
                                            <div class="fw-bold text-dark o_alert_title">
                                                <t t-esc="this.formatCurrency(state.student.fee_balance || 250)"/> tuition balance is overdue
                                            </div>
                                            <div class="text-muted small">Pay now to keep your registration active.</div>
                                        </div>
                                    </div>
                                    <button type="button" class="btn btn-primary btn-sm fw-semibold o_btn_pay_now"
                                            t-on-click="() => this.openMyInvoices()">
                                        Pay now
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- 4 KPI Cards Row -->
                        <div class="row g-3 mb-4">
                            <!-- Card 1: Cumulative GPA -->
                            <div class="col-12 col-sm-6 col-xl-3">
                                <div class="o_kpi_card_white p-3 rounded-3 bg-white border">
                                    <div class="text-muted small mb-1">Cumulative GPA</div>
                                    <div class="h3 fw-bold text-dark mb-2" t-esc="this.studentGpaDisplay"/>
                                    <div>
                                        <span class="badge o_kpi_pill_track">On track &#8226; min 2.00</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Card 2: Overall Attendance -->
                            <div class="col-12 col-sm-6 col-xl-3">
                                <div class="o_kpi_card_white p-3 rounded-3 bg-white border cursor-pointer"
                                     t-on-click="() => this.setActiveTab('attendance')">
                                    <div class="text-muted small mb-1">Overall attendance</div>
                                    <div class="h3 fw-bold text-dark mb-2" t-esc="(state.attendanceStats.rate || 62) + '%'"/>
                                    <div class="progress o_kpi_progress" style="height: 6px;">
                                        <div class="progress-bar bg-danger" role="progressbar"
                                             t-att-style="'width: ' + this.attendanceProgressWidth"/>
                                    </div>
                                </div>
                            </div>

                            <!-- Card 3: Credits Completed -->
                            <div class="col-12 col-sm-6 col-xl-3">
                                <div class="o_kpi_card_white p-3 rounded-3 bg-white border cursor-pointer"
                                     t-on-click="() => this.setActiveTab('curriculum')">
                                    <div class="text-muted small mb-1">Credits completed</div>
                                    <div class="h3 fw-bold text-dark mb-2">
                                        <t t-esc="state.student.completed_credits || 13"/>
                                        <span class="fs-6 fw-normal text-muted"> / 130</span>
                                    </div>
                                    <div class="progress o_kpi_progress" style="height: 6px;">
                                        <div class="progress-bar o_progress_bar_teal" role="progressbar"
                                             t-att-style="'width: ' + this.creditsProgressWidth"/>
                                    </div>
                                </div>
                            </div>

                            <!-- Card 4: Tuition Balance -->
                            <div class="col-12 col-sm-6 col-xl-3">
                                <div class="o_kpi_card_white p-3 rounded-3 bg-white border cursor-pointer"
                                     t-on-click="() => this.openMyInvoices()">
                                    <div class="text-muted small mb-1">Tuition balance</div>
                                    <div class="h3 fw-bold text-dark mb-2" t-esc="this.formatCurrency(state.student.fee_balance || 250)"/>
                                    <div>
                                        <span class="badge o_kpi_pill_due">Payment due</span>
                                    </div>
                                </div>
                            </div>
                        </div>"""

replacement = """            <t t-else="">
                <!-- ==================== TOP NAVIGATION & IDENTITY BAR ==================== -->
                <header class="o_student_navbar bg-white border-bottom sticky-top z-3 px-3 px-lg-4 py-2 shadow-xs">
                    <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-2">
                        <!-- Left: Student Info & Avatar -->
                        <div class="d-flex align-items-center gap-3">
                            <div class="o_student_header_avatar_wrap flex-shrink-0">
                                <t t-if="state.student.image_1920">
                                    <img t-att-src="'/web/image/university.student/' + state.student.id + '/image_1920'"
                                         class="o_student_header_avatar rounded-circle shadow-xs"
                                         alt="Student photo"/>
                                </t>
                                <t t-else="">
                                    <div class="o_student_avatar_placeholder rounded-circle bg-teal-subtle text-teal fw-bold d-flex align-items-center justify-content-center shadow-xs">
                                        <t t-esc="this.profileInitials"/>
                                    </div>
                                </t>
                            </div>
                            <div>
                                <div class="d-flex align-items-center gap-2 flex-wrap">
                                    <h1 class="h5 fw-bold text-dark mb-0" t-esc="state.student.name"/>
                                    <span class="badge bg-primary-subtle text-primary border border-primary-subtle font-monospace" t-esc="this.studentIdDisplay"/>
                                    <span class="badge bg-success-subtle text-success border border-success-subtle text-capitalize" t-esc="state.student.status || 'Active'"/>
                                </div>
                                <div class="text-muted small d-flex align-items-center gap-2 flex-wrap mt-1">
                                    <span class="fw-semibold text-secondary" t-esc="this.programDisplay"/>
                                    <t t-if="state.student.department_id">
                                        <span>&#8226;</span>
                                        <span><i class="fa fa-building-o me-1 text-muted"/> <t t-esc="state.student.department_id[1]"/></span>
                                    </t>
                                    <t t-if="state.student.advisor_id">
                                        <span>&#8226;</span>
                                        <span><i class="fa fa-user-circle-o me-1 text-muted"/> Advisor: <strong class="text-dark"><t t-esc="this.advisorDisplay"/></strong></span>
                                    </t>
                                </div>
                            </div>
                        </div>

                        <!-- Right: Action Buttons (Curriculum PDF, Request Transcript, Refresh) -->
                        <div class="d-flex align-items-center gap-2 flex-wrap">
                            <button type="button" class="btn btn-outline-secondary btn-sm fw-semibold rounded-2 shadow-xs d-flex align-items-center gap-2"
                                    t-on-click="() => this.printCurriculum()"
                                    title="Export Degree Curriculum PDF">
                                <i class="fa fa-file-pdf-o text-danger"/>
                                <span class="d-none d-sm-inline">Curriculum PDF</span>
                            </button>
                            <button type="button" class="btn btn-primary btn-sm fw-semibold rounded-2 shadow-xs d-flex align-items-center gap-2"
                                    t-on-click="() => this.openNewTranscriptRequest()"
                                    title="Request Official Sealed Transcript">
                                <i class="fa fa-file-text-o"/>
                                <span>Request Transcript</span>
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-sm rounded-2 shadow-xs"
                                    t-on-click="() => this.loadStudentData()"
                                    title="Reload Student Academic Records">
                                <i class="fa fa-refresh" t-att-class="{'fa-spin': state.loading}"/>
                            </button>
                        </div>
                    </div>

                    <!-- Top Navigation Tabs (Pills) -->
                    <nav class="nav nav-pills o_student_nav_pills gap-1 flex-nowrap overflow-x-auto pb-1 pt-1 border-top" aria-label="Student Navigation">
                        <button type="button"
                                class="nav-link py-1 px-3 d-flex align-items-center gap-2 fw-semibold rounded-pill text-nowrap"
                                t-att-class="{'active': state.activeTab === 'dashboard'}"
                                t-on-click="() => this.setActiveTab('dashboard')">
                            <i class="fa fa-dashboard"/>
                            <span>Overview</span>
                        </button>
                        <button type="button"
                                class="nav-link py-1 px-3 d-flex align-items-center gap-2 fw-semibold rounded-pill text-nowrap"
                                t-att-class="{'active': state.activeTab === 'classes'}"
                                t-on-click="() => this.setActiveTab('classes')">
                            <i class="fa fa-graduation-cap"/>
                            <span>My Classes</span>
                            <span class="badge rounded-pill bg-light text-dark border ms-1" t-esc="state.enrolledClasses.length"/>
                        </button>
                        <button type="button"
                                class="nav-link py-1 px-3 d-flex align-items-center gap-2 fw-semibold rounded-pill text-nowrap"
                                t-att-class="{'active': state.activeTab === 'schedule'}"
                                t-on-click="() => this.setActiveTab('schedule')">
                            <i class="fa fa-calendar"/>
                            <span>Timetable &amp; Schedule</span>
                        </button>
                        <button type="button"
                                class="nav-link py-1 px-3 d-flex align-items-center gap-2 fw-semibold rounded-pill text-nowrap"
                                t-att-class="{'active': state.activeTab === 'attendance'}"
                                t-on-click="() => this.setActiveTab('attendance')">
                            <i class="fa fa-check-circle"/>
                            <span>Attendance</span>
                            <span t-att-class="'badge rounded-pill ms-1 ' + (state.attendanceStats.rate >= 80 ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger')"
                                  t-esc="(state.attendanceStats.rate || 0) + '%'"/>
                        </button>
                        <button type="button"
                                class="nav-link py-1 px-3 d-flex align-items-center gap-2 fw-semibold rounded-pill text-nowrap"
                                t-att-class="{'active': state.activeTab === 'transcript'}"
                                t-on-click="() => this.setActiveTab('transcript')">
                            <i class="fa fa-certificate"/>
                            <span>Grades &amp; Transcript</span>
                            <span class="badge rounded-pill bg-primary-subtle text-primary ms-1" t-esc="'GPA ' + this.studentGpaDisplay"/>
                        </button>
                        <button type="button"
                                class="nav-link py-1 px-3 d-flex align-items-center gap-2 fw-semibold rounded-pill text-nowrap"
                                t-att-class="{'active': state.activeTab === 'curriculum'}"
                                t-on-click="() => this.setActiveTab('curriculum')">
                            <i class="fa fa-book"/>
                            <span>Curriculum Roadmap</span>
                            <span class="badge rounded-pill bg-light text-dark border ms-1" t-esc="(state.student.completed_credits || 0) + ' Cr'"/>
                        </button>
                        <button type="button"
                                class="nav-link py-1 px-3 d-flex align-items-center gap-2 fw-semibold rounded-pill text-nowrap"
                                t-att-class="{'active': state.activeTab === 'financial'}"
                                t-on-click="() => this.setActiveTab('financial')">
                            <i class="fa fa-credit-card"/>
                            <span>Tuition &amp; Fees</span>
                            <t t-if="state.student.fee_balance > 0">
                                <span class="badge rounded-pill bg-danger-subtle text-danger ms-1" t-esc="this.formatCurrency(state.student.fee_balance)"/>
                            </t>
                            <t t-else="">
                                <span class="badge rounded-pill bg-success-subtle text-success ms-1">Settled</span>
                            </t>
                        </button>
                        <button type="button"
                                class="nav-link py-1 px-3 d-flex align-items-center gap-2 fw-semibold rounded-pill text-nowrap"
                                t-att-class="{'active': state.activeTab === 'notices'}"
                                t-on-click="() => this.setActiveTab('notices')">
                            <i class="fa fa-bullhorn"/>
                            <span>Campus Notices</span>
                            <span t-if="state.counts.notices" class="badge rounded-pill bg-danger text-white ms-1" t-esc="state.counts.notices"/>
                        </button>
                    </nav>
                </header>

                <!-- ==================== DASHBOARD VIEW (when activeTab === 'dashboard') ==================== -->
                <t t-if="state.activeTab === 'dashboard'">
                    <div class="o_student_mockup_dashboard p-3 p-lg-4">
                        <!-- Top Header Welcome Hero Card -->
                        <div class="card border-0 shadow-sm p-4 rounded-3 bg-white mb-4 o_student_welcome_hero">
                            <div class="d-flex flex-wrap align-items-center justify-content-between gap-3">
                                <div>
                                    <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                                        <span class="badge bg-teal-subtle text-teal fw-bold">Academic Session: Fall 2026</span>
                                        <span class="text-muted small">&#8226; Year 2 Semester 1</span>
                                        <span t-att-class="'badge rounded-pill ' + this.studentStandingBadge.class" t-esc="this.studentStandingBadge.label"/>
                                    </div>
                                    <h2 class="h3 fw-bold text-dark mb-1" t-esc="this.greeting"/>
                                    <p class="text-secondary small mb-0">
                                        Here is your real-time academic progress, daily timetable schedule, and coursework standing.
                                    </p>
                                </div>
                                <div class="d-flex align-items-center gap-2 flex-wrap">
                                    <button type="button" class="btn btn-outline-secondary btn-sm fw-semibold shadow-xs"
                                            t-on-click="() => this.setActiveTab('schedule')">
                                        <i class="fa fa-calendar me-1"/> View Full Timetable
                                    </button>
                                    <button type="button" class="btn btn-teal btn-sm fw-semibold shadow-xs text-white"
                                            t-on-click="() => this.setActiveTab('classes')">
                                        <i class="fa fa-graduation-cap me-1"/> Enrolled Classes (<t t-esc="state.enrolledClasses.length"/>)
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Alert Banners Row (Side-by-side 2 Columns) -->
                        <div class="row g-3 mb-4">
                            <!-- Banner 1: Attendance Warning / Good Standing -->
                            <div class="col-12 col-lg-6">
                                <t t-if="state.attendanceStats.rate &lt; 80">
                                    <div class="o_alert_card o_alert_attendance_card d-flex align-items-center justify-content-between p-3 rounded-3">
                                        <div class="d-flex align-items-center gap-3">
                                            <div class="o_alert_icon_circle o_alert_icon_red d-flex align-items-center justify-content-center">
                                                <i class="fa fa-exclamation"/>
                                            </div>
                                            <div>
                                                <div class="fw-bold text-dark o_alert_title">
                                                    Attendance is <t t-esc="state.attendanceStats.rate || 62"/>%, below the 80% exam requirement
                                                </div>
                                                <div class="text-muted small">Missing additional classes risks exam disqualification.</div>
                                            </div>
                                        </div>
                                        <button type="button" class="btn btn-outline-secondary btn-sm bg-white fw-semibold o_alert_btn"
                                                t-on-click="() => this.setActiveTab('attendance')">
                                            Submit excuse
                                        </button>
                                    </div>
                                </t>
                                <t t-else="">
                                    <div class="card p-3 rounded-3 border-0 shadow-sm bg-white d-flex flex-row align-items-center justify-content-between">
                                        <div class="d-flex align-items-center gap-3">
                                            <div class="o_alert_icon_circle bg-success text-white d-flex align-items-center justify-content-center">
                                                <i class="fa fa-check"/>
                                            </div>
                                            <div>
                                                <div class="fw-bold text-dark">
                                                    Attendance in Good Standing (<t t-esc="state.attendanceStats.rate || 95"/>%)
                                                </div>
                                                <div class="text-muted small">You are fully eligible for all semester final examinations.</div>
                                            </div>
                                        </div>
                                        <button type="button" class="btn btn-outline-secondary btn-sm"
                                                t-on-click="() => this.setActiveTab('attendance')">
                                            View record
                                        </button>
                                    </div>
                                </t>
                            </div>

                            <!-- Banner 2: Tuition Overdue / Settled -->
                            <div class="col-12 col-lg-6">
                                <t t-if="state.student.fee_balance &gt; 0">
                                    <div class="o_alert_card o_alert_tuition_card d-flex align-items-center justify-content-between p-3 rounded-3">
                                        <div class="d-flex align-items-center gap-3">
                                            <div class="o_alert_icon_circle o_alert_icon_amber d-flex align-items-center justify-content-center">
                                                <i class="fa fa-dollar"/>
                                            </div>
                                            <div>
                                                <div class="fw-bold text-dark o_alert_title">
                                                    <t t-esc="this.formatCurrency(state.student.fee_balance)"/> tuition balance is overdue
                                                </div>
                                                <div class="text-muted small">Pay now to keep your registration and course access active.</div>
                                            </div>
                                        </div>
                                        <button type="button" class="btn btn-primary btn-sm fw-semibold o_btn_pay_now"
                                                t-on-click="() => this.openMyInvoices()">
                                            Pay now
                                        </button>
                                    </div>
                                </t>
                                <t t-else="">
                                    <div class="card p-3 rounded-3 border-0 shadow-sm bg-white d-flex flex-row align-items-center justify-content-between">
                                        <div class="d-flex align-items-center gap-3">
                                            <div class="o_alert_icon_circle bg-success text-white d-flex align-items-center justify-content-center">
                                                <i class="fa fa-shield"/>
                                            </div>
                                            <div>
                                                <div class="fw-bold text-dark">Tuition Account Settled</div>
                                                <div class="text-muted small">All tuition and registration fees are paid in full for this term.</div>
                                            </div>
                                        </div>
                                        <button type="button" class="btn btn-outline-secondary btn-sm"
                                                t-on-click="() => this.setActiveTab('financial')">
                                            Fee Ledger
                                        </button>
                                    </div>
                                </t>
                            </div>
                        </div>

                        <!-- 5 Key Academic Metric KPI Cards Row -->
                        <div class="row g-3 mb-4">
                            <!-- Card 1: Cumulative GPA -->
                            <div class="col-12 col-sm-6 col-xl">
                                <div class="o_kpi_card_white p-3 rounded-3 bg-white border h-100 cursor-pointer"
                                     t-on-click="() => this.setActiveTab('transcript')">
                                    <div class="d-flex align-items-center justify-content-between mb-1">
                                        <span class="text-muted small fw-semibold">Cumulative GPA</span>
                                        <i class="fa fa-graduation-cap text-primary small"/>
                                    </div>
                                    <div class="h3 fw-bold text-dark mb-1" t-esc="this.studentGpaDisplay"/>
                                    <div class="d-flex align-items-center gap-1">
                                        <span t-att-class="'badge ' + this.studentStandingBadge.class" t-esc="this.studentStandingBadge.label"/>
                                    </div>
                                </div>
                            </div>

                            <!-- Card 2: Overall Attendance -->
                            <div class="col-12 col-sm-6 col-xl">
                                <div class="o_kpi_card_white p-3 rounded-3 bg-white border h-100 cursor-pointer"
                                     t-on-click="() => this.setActiveTab('attendance')">
                                    <div class="d-flex align-items-center justify-content-between mb-1">
                                        <span class="text-muted small fw-semibold">Overall Attendance</span>
                                        <i class="fa fa-check-circle text-success small"/>
                                    </div>
                                    <div class="h3 fw-bold text-dark mb-1" t-esc="(state.attendanceStats.rate || 0) + '%'"/>
                                    <div class="progress o_kpi_progress mb-1" style="height: 5px;">
                                        <div class="progress-bar" role="progressbar"
                                             t-att-class="state.attendanceStats.rate &gt;= 80 ? 'bg-success' : 'bg-danger'"
                                             t-att-style="'width: ' + this.attendanceProgressWidth"/>
                                    </div>
                                    <div class="text-muted very-small d-flex justify-content-between">
                                        <span>Present: <t t-esc="state.attendanceStats.present || 0"/></span>
                                        <span>Absent: <t t-esc="state.attendanceStats.absent || 0"/></span>
                                    </div>
                                </div>
                            </div>

                            <!-- Card 3: Credits Completed -->
                            <div class="col-12 col-sm-6 col-xl">
                                <div class="o_kpi_card_white p-3 rounded-3 bg-white border h-100 cursor-pointer"
                                     t-on-click="() => this.setActiveTab('curriculum')">
                                    <div class="d-flex align-items-center justify-content-between mb-1">
                                        <span class="text-muted small fw-semibold">Completed Credits</span>
                                        <i class="fa fa-book text-info small"/>
                                    </div>
                                    <div class="h3 fw-bold text-dark mb-1">
                                        <t t-esc="state.student.completed_credits || 13"/>
                                        <span class="fs-6 fw-normal text-muted"> / 130</span>
                                    </div>
                                    <div class="progress o_kpi_progress mb-1" style="height: 5px;">
                                        <div class="progress-bar o_progress_bar_teal" role="progressbar"
                                             t-att-style="'width: ' + this.creditsProgressWidth"/>
                                    </div>
                                    <div class="text-muted very-small" t-esc="this.creditsCompletionPercent + '% of degree completed'"/>
                                </div>
                            </div>

                            <!-- Card 4: Enrolled Course Load -->
                            <div class="col-12 col-sm-6 col-xl">
                                <div class="o_kpi_card_white p-3 rounded-3 bg-white border h-100 cursor-pointer"
                                     t-on-click="() => this.setActiveTab('classes')">
                                    <div class="d-flex align-items-center justify-content-between mb-1">
                                        <span class="text-muted small fw-semibold">Term Enrolled Load</span>
                                        <i class="fa fa-th-list text-warning small"/>
                                    </div>
                                    <div class="h3 fw-bold text-dark mb-1">
                                        <t t-esc="state.enrolledClasses.length"/>
                                        <span class="fs-6 fw-normal text-muted"> Courses</span>
                                    </div>
                                    <div class="text-muted very-small">
                                        <span class="badge bg-light text-dark border"><t t-esc="this.totalEnrolledCredits"/> Total Credits</span>
                                        <span class="ms-1">Fall 2026</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Card 5: Tuition Balance -->
                            <div class="col-12 col-sm-6 col-xl">
                                <div class="o_kpi_card_white p-3 rounded-3 bg-white border h-100 cursor-pointer"
                                     t-on-click="() => this.setActiveTab('financial')">
                                    <div class="d-flex align-items-center justify-content-between mb-1">
                                        <span class="text-muted small fw-semibold">Tuition Status</span>
                                        <i class="fa fa-credit-card text-success small"/>
                                    </div>
                                    <div class="h3 fw-bold text-dark mb-1" t-esc="this.formatCurrency(state.student.fee_balance || 0)"/>
                                    <div>
                                        <t t-if="state.student.fee_balance &gt; 0">
                                            <span class="badge o_kpi_pill_due">Payment Due</span>
                                        </t>
                                        <t t-else="">
                                            <span class="badge bg-success-subtle text-success border border-success-subtle">Account Settled</span>
                                        </t>
                                    </div>
                                </div>
                            </div>
                        </div>"""

# Normalize line endings
c_norm = c.replace('\r\n', '\n')
target_norm = target_start.replace('\r\n', '\n')
replacement_norm = replacement.replace('\r\n', '\n')

if target_norm in c_norm:
    c_norm = c_norm.replace(target_norm, replacement_norm, 1)
    # Check XML validity before saving
    ET.fromstring(c_norm)
    with open('static/src/school_management/student_dashboard_shell.xml', 'w', encoding='utf-8') as f:
        f.write(c_norm)
    print("SUCCESS: student_dashboard_shell.xml updated and valid!")
else:
    print("ERROR: Target block not found in student_dashboard_shell.xml")
