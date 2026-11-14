/** @odoo-module **/

import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

// Inline Chart.js plugin to draw total students in the center of doughnut
const doughnutCenterText = {
    id: "doughnutCenterText",
    afterDraw(chart) {
        const opts = chart.options?.plugins?.centerText;
        if (!opts || !chart.data?.datasets?.length) return;
        const first = chart.getDatasetMeta(0)?.data?.[0];
        if (!first) return;
        const values = chart.data.datasets[0].data || [];
        const total = opts.customValue || values.reduce((sum, v) => sum + (Number(v) || 0), 0);
        const x = typeof first.x === "number" ? first.x : ((chart.chartArea.left + chart.chartArea.right) / 2);
        const y = typeof first.y === "number" ? first.y : ((chart.chartArea.top + chart.chartArea.bottom) / 2);
        const { ctx } = chart;
        ctx.save();
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = opts.valueColor || "#0f172a";
        ctx.font = `800 ${opts.valueSize || 24}px system-ui, -apple-system, sans-serif`;
        const formattedTotal = Number(total).toLocaleString();
        ctx.fillText(formattedTotal, x, y - 8);
        if (opts.label) {
            ctx.fillStyle = opts.labelColor || "#64748b";
            ctx.font = "600 11px system-ui, -apple-system, sans-serif";
            ctx.fillText(opts.label, x, y + 14);
        }
        ctx.restore();
    },
};

class SchoolDashboardShell extends Component {
    static template = "school_management.DashboardShell";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.chartEnrollmentRef = useRef("chart_enrollment");
        this.chartProgramRef = useRef("chart_program");
        this.chartStatusRef = useRef("chart_status");
        this.charts = [];

        this.state = useState({
            dashboard: null,
            chartData: null,
            error: null,
            isLoading: true,
            isRefreshing: false,
            isNavigating: false,
            lastUpdated: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            academicPeriod: {
                year: "",
                semester: "",
                label: "",
            },
            filters: {
                yearId: false,
                semesterId: false,
            },
            filterOptions: {
                academicYears: [],
                semesters: [],
            },
            sidebarCollapsed: localStorage.getItem("exec_sidebar_collapsed") === "1",
            showProfileMenu: false,
            activeRoleOverride: null,
            activeNavId: "dashboard",
        });

        onWillStart(async () => {
            try {
                const isStudent = await user.hasGroup("school_management.group_school_student");
                const isTeacher = (await user.hasGroup("school_management.group_school_teacher")) ||
                                  (await user.hasGroup("school_management.group_university_teacher"));
                const isAdminOrLeadership = (await user.hasGroup("school_management.group_school_admin")) ||
                                            (await user.hasGroup("base.group_system")) ||
                                            (await user.hasGroup("school_management.group_school_registrar")) ||
                                            (await user.hasGroup("school_management.group_school_hod")) ||
                                            (await user.hasGroup("school_management.group_school_dean"));
                if (isStudent && !isAdminOrLeadership && !isTeacher) {
                    await this.action.doAction("school_management.action_student_dashboard_shell", {
                        clearBreadcrumbs: true,
                    });
                    return;
                }
                if (isTeacher && !isAdminOrLeadership) {
                    await this.action.doAction("school_management.action_teacher_dashboard_shell", {
                        clearBreadcrumbs: true,
                    });
                    return;
                }
                await Promise.all([
                    loadBundle("web.chartjs_lib"),
                    this.loadFilterOptions(),
                ]);
                await this.loadDashboardData();
            } catch (error) {
                console.error("Failed to initialize executive dashboard", error);
                this.state.error = error.message || "Unable to load dashboard data.";
            } finally {
                this.state.isLoading = false;
            }
        });

        onMounted(() => {
            this.renderCharts();
        });

        onWillUnmount(() => {
            this.destroyCharts();
        });
    }

    destroyCharts() {
        this.charts.forEach((chart) => {
            try {
                chart.destroy();
            } catch (err) {
                console.warn("Chart destroy warning", err);
            }
        });
        this.charts = [];
    }

    async loadFilterOptions(yearId = false) {
        try {
            const options = await this.orm.call(
                "school.dashboard",
                "get_filter_options",
                yearId ? [Number(yearId)] : []
            );
            this.state.filterOptions.academicYears = options.academic_years || [];
            this.state.filterOptions.semesters = options.semesters || [];
            this.state.filters.yearId = options.selected_year_id || false;
            this.state.filters.semesterId = options.selected_semester_id || false;
            this.updateAcademicPeriodLabel();
        } catch (error) {
            console.error("Failed to load filter options", error);
        }
    }

    updateAcademicPeriodLabel() {
        const year = this.state.filterOptions.academicYears.find(
            (item) => item.id === Number(this.state.filters.yearId)
        );
        const semester = this.state.filterOptions.semesters.find(
            (item) => item.id === Number(this.state.filters.semesterId)
        );
        this.state.academicPeriod.year = year?.name || "";
        this.state.academicPeriod.semester = semester?.name || "";
        this.state.academicPeriod.label = [semester?.name, year?.name].filter(Boolean).join(" · ");
    }

    async changeFilter(name, value) {
        this.state.filters[name] = Number(value) || false;
        if (name === "yearId") {
            await this.loadFilterOptions(this.state.filters.yearId);
        } else {
            this.updateAcademicPeriodLabel();
        }
        await this.reload();
    }

    async loadDashboardData() {
        const result = await this.orm.call("school.dashboard", "get_role_dashboard_data", [
            this.state.filters.yearId || false,
            this.state.filters.semesterId || false,
        ]);
        this.state.dashboard = result.dashboard || null;
        this.state.chartData = result.chart_data || null;
        this.state.filters.yearId = result.selected_year_id || false;
        this.state.filters.semesterId = result.selected_semester_id || false;
        this.updateAcademicPeriodLabel();
    }

    async reload() {
        if (this.state.isRefreshing) return;
        this.state.isRefreshing = true;
        this.state.error = null;
        try {
            await this.loadDashboardData();
            this.state.lastUpdated = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            setTimeout(() => {
                this.renderCharts();
            }, 60);
        } catch (error) {
            console.error("Failed to refresh dashboard data", error);
            this.state.error = error.message || "Unable to refresh dashboard data.";
        } finally {
            this.state.isRefreshing = false;
        }
    }

    async navigate(actionXmlId) {
        if (this.state.isNavigating || !actionXmlId) {
            return;
        }
        this.state.isNavigating = true;
        try {
            await this.action.doAction(actionXmlId);
        } catch (error) {
            console.error(`Failed to navigate to ${actionXmlId}`, error);
            this.notification?.add(error.message || "Failed to open view", { type: "danger" });
        } finally {
            this.state.isNavigating = false;
        }
    }

    async quickCreate(resModel, name) {
        try {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name,
                res_model: resModel,
                views: [[false, "form"]],
                view_mode: "form",
                target: "current",
            });
        } catch (error) {
            console.error(`Failed to open ${name} form`, error);
            this.notification?.add(error.message || `Unable to open ${name}.`, { type: "danger" });
        }
    }

    handleActionClick(actionName) {
        if (actionName && typeof this[actionName] === "function") {
            this[actionName]();
        }
    }

    // Action Handlers
    openAdmissions() {
        this.navigate("school_management.action_university_admission_application");
    }

    openConflicts() {
        this.navigate("school_management.action_university_schedule_conflicts");
    }

    openStudents() {
        this.navigate("school_management.action_university_student");
    }

    openTeachers() {
        this.navigate("school_management.action_university_teacher");
    }

    openSubjects() {
        this.navigate("school_management.action_university_subject");
    }

    openDepartments() {
        this.navigate("school_management.action_university_department");
    }

    openEnrollments() {
        this.navigate("school_management.action_university_enrollment");
    }

    openStudentDetails(studentId) {
        if (studentId) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "university.student",
                res_id: studentId,
                views: [[false, "form"]],
                target: "current",
            });
        } else {
            this.openStudents();
        }
    }


    openAttendance() {
        this.navigate("school_management.action_university_attendance");
    }

    openFees() {
        this.navigate("school_management.action_university_fee");
    }

    quickNewStudent() {
        this.quickCreate("university.student", "New Student");
    }

    quickViewClasses() {
        this.navigate("school_management.action_university_class_section");
    }

    quickRecordAttendance() {
        this.navigate("school_management.action_university_attendance");
    }

    quickCreateFee() {
        this.quickCreate("university.fee", "New Fee Invoice");
    }

    quickProcessPayment() {
        this.quickCreate("university.payment", "Record Payment");
    }

    openReports() {
        this.navigate("school_management.action_university_report_card");
    }

    openExams() {
        this.navigate("school_management.action_university_exam");
    }

    quickTimetable() {
        this.action.doAction("school_management.action_university_schedule_view");
    }

    quickGradeSubmissions() {
        this.navigate("school_management.action_university_assignment_submission");
    }

    quickAdvisees() {
        this.navigate("school_management.action_university_student");
    }

    quickLessonPlans() {
        this.navigate("school_management.action_university_lesson_plan");
    }

    openAttendanceSheet() {
        this.action.doAction("school_management.action_university_attendance_session");
    }

    formatCurrency(amount) {
        const val = Number(amount) || 0;
        const symbol = this.state.dashboard?.currency_symbol || "";
        return symbol + val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }

    formatNumber(val) {
        return (Number(val) || 0).toLocaleString();
    }

    get isExecutiveLayout() {
        return Boolean(this.state.dashboard?.kpi_five && this.state.dashboard.kpi_five.length);
    }

    get kpiFive() {
        return this.state.dashboard?.kpi_five || [];
    }

    get recentEnrollments() {
        return this.state.dashboard?.recent_enrollments || [];
    }

    getStatusBadgeClass(status, statusClass = '') {
        if (statusClass && !statusClass.includes('text-secondary') && !statusClass.includes('bg-light')) {
            return statusClass;
        }
        const s = String(status || '').toLowerCase().trim();
        if (s === 'active' || s === 'enrolled' || s === 'approved' || s === 'good_standing' || s === 'completed') {
            return 'bg-success-subtle text-success border border-success-subtle';
        }
        if (s === 'pending' || s === 'to_approve' || s === 'review' || s === 'in_progress' || s === 'suspended') {
            return 'bg-warning-subtle text-warning border border-warning-subtle';
        }
        if (s === 'draft' || s === 'planning' || s === 'planned') {
            return 'bg-secondary-subtle text-secondary border border-secondary-subtle';
        }
        if (s === 'dropped' || s === 'withdrawn' || s === 'cancelled' || s === 'rejected' || s === 'overdue') {
            return 'bg-danger-subtle text-danger border border-danger-subtle';
        }
        if (s === 'graduated') {
            return 'bg-info-subtle text-info border border-info-subtle';
        }
        return 'bg-success-subtle text-success border border-success-subtle';
    }

    get topDepartments() {
        return this.state.dashboard?.top_departments || [];
    }

    get lowGpaAlert() {
        return this.state.dashboard?.low_gpa_alert || {};
    }

    get upcomingEvents() {
        return this.state.dashboard?.upcoming_events || [];
    }

    get pendingReports() {
        return this.state.dashboard?.pending_reports || {};
    }

    get studentStatusBreakdown() {
        return this.state.chartData?.student_status?.breakdown || [];
    }

    get enrollmentActiveBadge() {
        return this.state.chartData?.enrollment_trend?.active_badge || "";
    }

    get userGreeting() {
        return this.state.dashboard?.user_greeting || "";
    }

    get userName() {
        return this.state.dashboard?.user_name || "";
    }

    get subtitle() {
        return this.state.dashboard?.subtitle || "University Executive Dashboard • Real-time Academic & Administrative Analytics";
    }

    get trendTitle() {
        return this.state.chartData?.trend_title || "Enrollment Overview";
    }

    get trendSubtitle() {
        return this.state.chartData?.trend_subtitle || "Historical term comparisons with calibrated vertical scaling";
    }

    get trendLegend() {
        const role = this.state.dashboard?.user_role;
        if (role === "teacher") return "Class Sessions";
        if (role === "hod") return "Department Load";
        return "Enrolled Students";
    }

    get distributionTitle() {
        return this.state.chartData?.distribution_title || "Student Distribution";
    }

    get distributionSubtitle() {
        return this.state.chartData?.distribution_subtitle || "By academic faculty & program";
    }

    get quickOpsBadge() {
        const role = this.state.dashboard?.user_role;
        if (role === "dean") return "Faculty Leadership";
        if (role === "hod") return "Department Leadership";
        if (role === "teacher") return "Teaching Shortcuts";
        return "Executive Shortcuts";
    }

    toggleSidebarCollapse() {
        this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
        try {
            localStorage.setItem("exec_sidebar_collapsed", this.state.sidebarCollapsed ? "1" : "0");
        } catch {}
    }

    toggleProfileMenu() {
        this.state.showProfileMenu = !this.state.showProfileMenu;
    }

    closeProfileMenu() {
        this.state.showProfileMenu = false;
    }

    focusGlobalSearch() {
        const input = document.querySelector(".o_filter_select");
        if (input) {
            input.focus();
        }
    }

    openHelpSupport() {
        this.notification?.add("Need administrative assistance? Contact system administration or visit university.edu/help", {
            title: "Help & Support",
            type: "info",
        });
    }

    openUserSettings() {
        this.state.showProfileMenu = false;
        this.action.doAction("base.action_res_users_my");
    }

    logout() {
        window.location.href = "/web/session/logout";
    }

    async switchRole(role) {
        this.state.showProfileMenu = false;
        if (role === "student") {
            await this.action.doAction("school_management.action_student_dashboard_shell", {
                clearBreadcrumbs: true,
            });
        } else {
            this.state.activeRoleOverride = role;
            this.state.activeNavId = "dashboard";
        }
    }

    openSpreadsheetAnalytics() {
        return this.action.doAction("spreadsheet_dashboard.ir_actions_dashboard_action");
    }

    handleSidebarItemClick(item) {
        this.state.showProfileMenu = false;
        if (item.id === "dashboard") {
            this.state.activeNavId = "dashboard";
            return;
        }
        if (item.id === "approvals" || item.id === "needs_action") {
            this.openAdmissions();
        } else if (item.id === "courses") {
            this.quickTimetable();
        } else if (item.id === "lecturers" || item.id === "faculty_staff") {
            this.openTeachers();
        } else if (item.id === "students") {
            this.openStudents();
        } else if (item.id === "departments") {
            this.navigate("school_management.action_university_department");
        } else if (item.id === "attendance") {
            this.openAttendance();
        } else if (item.id === "grades") {
            this.openReports();
        } else if (item.id === "reports") {
            this.openReports();
        } else if (item.id === "budget") {
            this.notification?.add("Budget tracking: Current fiscal allocation is 84% utilized.", { type: "info" });
        } else if (item.id === "accreditation") {
            this.notification?.add("Institutional Accreditation: Good standing through 2029.", { type: "info" });
        } else if (item.id === "users_roles") {
            this.navigate("base.action_res_users");
        } else if (item.id === "academic_setup") {
            this.navigate("school_management.action_university_program");
        } else if (item.id === "registration") {
            this.navigate("school_management.action_university_enrollment");
        } else if (item.id === "finance_fees") {
            this.openFees();
        } else if (item.id === "notices") {
            this.navigate("school_management.action_university_notice_board");
        } else if (item.id === "audit_log") {
            this.navigate("base.action_res_users");
        } else if (item.id === "settings") {
            this.openUserSettings();
        }
    }

    get effectiveRole() {
        if (this.state.activeRoleOverride) {
            return this.state.activeRoleOverride;
        }
        const role = this.state.dashboard?.user_role;
        if (role === "hod") return "hod";
        if (role === "dean") return "dean";
        return "admin";
    }

    get profileName() {
        const role = this.effectiveRole;
        if (role === "hod") return "Prof. Paul Farmer";
        if (role === "dean") return "Prof. Anna Reyes";
        return "Admin";
    }

    get profileInitials() {
        const role = this.effectiveRole;
        if (role === "hod") return "PF";
        if (role === "dean") return "AR";
        return "AD";
    }

    get profileRole() {
        const role = this.effectiveRole;
        if (role === "hod") return "Head of Nursing";
        if (role === "dean") return "Dean • Health Sciences";
        return "Administrator";
    }

    get execSidebarGroups() {
        const role = this.effectiveRole;
        const activeNav = this.state.activeNavId;

        if (role === "hod") {
            return [
                {
                    id: "overview",
                    label: "Overview",
                    items: [
                        { id: "dashboard", label: "Dashboard", iconSvg: "home", isActive: activeNav === "dashboard" },
                    ],
                },
                {
                    id: "decisions",
                    label: "Decisions",
                    items: [
                        { id: "approvals", label: "Approvals", iconSvg: "approvals", badge: "9", badgeClass: "o_badge_teal_solid", dotClass: "o_dot_teal", isActive: activeNav === "approvals" },
                    ],
                },
                {
                    id: "teaching",
                    label: "Teaching",
                    items: [
                        { id: "courses", label: "Courses & timetable", iconSvg: "schedule", isActive: activeNav === "courses" },
                        { id: "lecturers", label: "Lecturers", iconSvg: "users", isActive: activeNav === "lecturers" },
                        { id: "students", label: "Students", iconSvg: "users", isActive: activeNav === "students" },
                    ],
                },
                {
                    id: "monitor",
                    label: "Monitor",
                    items: [
                        { id: "attendance", label: "Attendance", iconSvg: "attendance", badge: "37", badgeClass: "o_badge_red", dotClass: "o_dot_red", isActive: activeNav === "attendance" },
                        { id: "grades", label: "Grades", iconSvg: "grades", isActive: activeNav === "grades" },
                        { id: "reports", label: "Reports", iconSvg: "reports", isActive: activeNav === "reports" },
                    ],
                },
            ];
        }

        if (role === "dean") {
            return [
                {
                    id: "overview",
                    label: "Overview",
                    items: [
                        { id: "dashboard", label: "Dashboard", iconSvg: "home", isActive: activeNav === "dashboard" },
                    ],
                },
                {
                    id: "decisions",
                    label: "Decisions",
                    items: [
                        { id: "approvals", label: "Approvals", iconSvg: "approvals", badge: "4", badgeClass: "o_badge_red", dotClass: "o_dot_red", isActive: activeNav === "approvals" },
                    ],
                },
                {
                    id: "faculty",
                    label: "Faculty",
                    items: [
                        { id: "departments", label: "Departments", iconSvg: "building", isActive: activeNav === "departments" },
                        { id: "students", label: "Students", iconSvg: "users", isActive: activeNav === "students" },
                        { id: "faculty_staff", label: "Faculty staff", iconSvg: "users", isActive: activeNav === "faculty_staff" },
                    ],
                },
                {
                    id: "planning",
                    label: "Planning",
                    items: [
                        { id: "budget", label: "Budget", iconSvg: "budget", badge: "84%", badgeClass: "o_badge_amber", dotClass: "o_dot_amber", isActive: activeNav === "budget" },
                        { id: "accreditation", label: "Accreditation", iconSvg: "shield", isActive: activeNav === "accreditation" },
                        { id: "reports", label: "Reports", iconSvg: "reports", isActive: activeNav === "reports" },
                    ],
                },
            ];
        }

        // Default: Admin
        return [
            {
                id: "overview",
                label: "Overview",
                items: [
                    { id: "dashboard", label: "Dashboard", iconSvg: "home", isActive: activeNav === "dashboard" },
                ],
            },
            {
                id: "tasks",
                label: "Tasks",
                items: [
                    { id: "needs_action", label: "Needs action", iconSvg: "approvals", isActive: activeNav === "needs_action" },
                ],
            },
            {
                id: "people",
                label: "People",
                items: [
                    { id: "users_roles", label: "Users & roles", iconSvg: "users", isActive: activeNav === "users_roles" },
                ],
            },
            {
                id: "setup",
                label: "Setup",
                items: [
                    { id: "academic_setup", label: "Academic setup", iconSvg: "curriculum", isActive: activeNav === "academic_setup" },
                    { id: "registration", label: "Registration", iconSvg: "registration", isActive: activeNav === "registration" },
                    { id: "finance_fees", label: "Finance & fees", iconSvg: "tuition", isActive: activeNav === "finance_fees" },
                    { id: "notices", label: "Notices", iconSvg: "notices", isActive: activeNav === "notices" },
                ],
            },
            {
                id: "system",
                label: "System",
                items: [
                    { id: "reports", label: "Reports", iconSvg: "reports", isActive: activeNav === "reports" },
                    { id: "audit_log", label: "Audit log", iconSvg: "audit", isActive: activeNav === "audit_log" },
                    { id: "settings", label: "Settings", iconSvg: "settings", isActive: activeNav === "settings" },
                ],
            },
        ];
    }

    get kpiCards() {
        const kpis = this.state.dashboard?.kpis;
        if (!kpis) return [];

        const cards = [];

        // Block 1: Demographics / Teaching Load
        if (kpis.demographics) {
            const d = kpis.demographics;
            const stu = d.students || {};
            const staff = d.staff || {};
            cards.push({
                key: "demographics",
                category: d.category || "Demographics",
                color: d.color || "primary",
                icon: d.icon || "fa-users",
                action: d.action || "openStudents",
                metric1: {
                    label: stu.label || "Enrolled Students",
                    value: this.formatNumber(stu.value || 0),
                    targetText: `/ Target ${this.formatNumber(stu.target || 0)}`,
                    growthText: stu.growth || "",
                    growthClass: "bg-success-subtle text-success",
                    progress: stu.progress || 0,
                },
                metric2: {
                    label: staff.label || "Academic Staff",
                    value: this.formatNumber(staff.value || 0),
                    targetText: `/ Target ${this.formatNumber(staff.target || 0)}`,
                    statusText: staff.growth || "",
                    statusClass: "bg-success-subtle text-success",
                },
            });
        }

        // Block 2: Performance
        if (kpis.performance) {
            const p = kpis.performance;
            cards.push({
                key: "performance",
                category: p.category || "Performance",
                color: p.color || "indigo",
                icon: p.icon || "fa-calendar-check-o",
                action: p.action || "openAttendance",
                metric1: {
                    label: p.label || "Attendance Rate",
                    value: `${p.attendance_rate || 0}%`,
                    targetText: p.target ? `Target: ${p.target}` : "",
                    growthText: p.growth || "",
                    growthClass: "bg-success-subtle text-success",
                    progress: p.progress || p.attendance_rate || 0,
                },
                metric2: {
                    label: "Health Status",
                    value: p.status || "",
                    statusText: "",
                    statusClass: "bg-success-subtle text-success",
                },
            });
        }

        // Block 3: Financials / Academic Programs / Class Sections / Grading Queue
        if (kpis.financials) {
            const f = kpis.financials;
            const isCount = f.is_count;
            const valFormatted = isCount ? this.formatNumber(f.collected || 0) : this.formatCurrency(f.collected || 0);
            const projFormatted = isCount ? this.formatNumber(f.projected || 0) : this.formatCurrency(f.projected || 0);
            cards.push({
                key: "financials",
                category: f.category || "Financials",
                color: f.color || "success",
                icon: f.icon || "fa-credit-card",
                action: f.action || "openFees",
                metric1: {
                    label: f.label || "Tuition Collection",
                    value: valFormatted,
                    targetText: "",
                    growthText: f.target_rate || "",
                    growthClass: f.color === "warning" ? "bg-warning text-dark" : "bg-success text-white",
                    progress: f.progress || 0,
                },
                metric2: {
                    label: f.sub_label || "Total Invoiced",
                    value: projFormatted,
                    statusText: "",
                },
            });
        }

        // Block 4: Admissions / Reviews / Advising
        if (kpis.admissions) {
            const a = kpis.admissions;
            cards.push({
                key: "admissions",
                category: a.category || "Admissions",
                color: a.color || "danger",
                icon: a.icon || "fa-user-plus",
                action: a.action || "openAdmissions",
                metric1: {
                    label: a.label || "Pending Reviews",
                    value: this.formatNumber(a.pending || 0),
                    targetText: "",
                    growthText: a.target || "",
                    growthClass: a.color === "info" ? "bg-info-subtle text-info" : "bg-danger-subtle text-danger",
                    progress: a.progress || 0,
                },
                metric2: {
                    label: a.sub_label || "Awaiting Review",
                    value: a.status || "Action required",
                    statusText: "",
                    statusClass: "bg-white text-primary border",
                },
            });
        }

        return cards;
    }

    get quickOps() {
        const role = this.state.dashboard?.user_role;

        if (role === "dean") {
            return [
                { id: "classes", title: "Faculty Classes", desc: "Class sections", icon: "fa-calendar", color: "info", action: "quickViewClasses" },
                { id: "staff", title: "Faculty Teachers", desc: "Teaching staff", icon: "fa-users", color: "primary", action: "openTeachers" },
                { id: "timetable", title: "Timetable", desc: "Campus schedule", icon: "fa-calendar-check-o", color: "purple", action: "quickTimetable" },
                { id: "sheet", title: "Attendance Sheet", desc: "Faculty records", icon: "fa-check-square-o", color: "success", action: "openAttendanceSheet" },
                { id: "grades", title: "Grade Reviews", desc: "Submissions & tasks", icon: "fa-tasks", color: "warning", action: "quickGradeSubmissions" },
                { id: "conflicts", title: "Room Conflicts", desc: "Schedule issues", icon: "fa-exclamation-triangle", color: "danger", action: "openConflicts" },
            ];
        }

        if (role === "hod") {
            return [
                { id: "classes", title: "Dept Classes", desc: "Class sections", icon: "fa-calendar", color: "info", action: "quickViewClasses" },
                { id: "staff", title: "Dept Teachers", desc: "Department staff", icon: "fa-users", color: "primary", action: "openTeachers" },
                { id: "attendance", title: "Take Attendance", desc: "Mark presence", icon: "fa-check-square-o", color: "success", action: "quickRecordAttendance" },
                { id: "sheet", title: "Attendance Sheet", desc: "Monthly report", icon: "fa-calendar-check-o", color: "purple", action: "openAttendanceSheet" },
                { id: "grading", title: "Grade Reviews", desc: "Pending reviews", icon: "fa-tasks", color: "warning", action: "quickGradeSubmissions" },
                { id: "conflicts", title: "Timetable Issues", desc: "Resolve conflicts", icon: "fa-exclamation-triangle", color: "danger", action: "openConflicts" },
            ];
        }

        if (role === "teacher") {
            return [
                { id: "attendance", title: "Take Attendance", desc: "Class session", icon: "fa-check-square-o", color: "success", action: "quickRecordAttendance" },
                { id: "sheet", title: "Attendance Sheet", desc: "Student registry", icon: "fa-calendar-check-o", color: "indigo", action: "openAttendanceSheet" },
                { id: "timetable", title: "My Timetable", desc: "Weekly schedule", icon: "fa-calendar", color: "purple", action: "quickTimetable" },
                { id: "grading", title: "Grade Work", desc: "Assignment queue", icon: "fa-tasks", color: "warning", action: "quickGradeSubmissions" },
                { id: "advisees", title: "Advisees", desc: "Student success", icon: "fa-graduation-cap", color: "info", action: "quickAdvisees" },
                { id: "lesson_plans", title: "Lesson Plans", desc: "Course syllabus", icon: "fa-file-text-o", color: "secondary", action: "quickLessonPlans" },
            ];
        }

        // Default Admin / Registrar
        return [
            { id: "add_student", title: "Add Student", desc: "Registration", icon: "fa-user-plus", color: "primary", action: "quickNewStudent" },
            { id: "view_classes", title: "View Classes", desc: "Class sections", icon: "fa-calendar", color: "info", action: "quickViewClasses" },
            { id: "attendance", title: "Attendance", desc: "Take presence", icon: "fa-check-square-o", color: "success", action: "quickRecordAttendance" },
            { id: "create_invoice", title: "Create Invoice", desc: "Tuition fees", icon: "fa-file-text-o", color: "warning", action: "quickCreateFee" },
            { id: "record_payment", title: "Record Payment", desc: "Receive funds", icon: "fa-credit-card", color: "purple", action: "quickProcessPayment" },
            { id: "conflicts", title: "Conflicts", desc: "Room schedule", icon: "fa-exclamation-triangle", color: "danger", action: "openConflicts" },
        ];
    }

    renderCharts() {
        this.destroyCharts();
        if (!this.state.chartData || !window.Chart) return;

        // 1. Enrollment Overview / Trend Chart (Smooth Curved Area/Line Chart matching Mockup)
        if (this.chartEnrollmentRef.el) {
            const trend = this.state.chartData.enrollment_trend || { labels: [], data: [] };
            const trendData = trend.data || [];
            const ctxEnrollment = this.chartEnrollmentRef.el.getContext("2d");
            const maxVal = Math.max(...trendData, 20);
            const ySuggestedMax = Math.ceil((maxVal * 1.15) / 100) * 100;
            const minVal = trendData.length ? Math.min(...trendData) : 0;
            const ySuggestedMin = trendData.length ? Math.max(0, Math.floor((minVal * 0.85) / 100) * 100) : 0;

            // Subtle gradient fill under the line
            const gradient = ctxEnrollment.createLinearGradient(0, 0, 0, 260);
            gradient.addColorStop(0, "rgba(79, 70, 229, 0.22)");
            gradient.addColorStop(1, "rgba(79, 70, 229, 0.00)");

            this.charts.push(new window.Chart(ctxEnrollment, {
                type: "line",
                data: {
                    labels: trend.labels,
                    datasets: [{
                        label: "Enrolled Students",
                        data: trendData,
                        borderColor: "#4f46e5",
                        borderWidth: 3,
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: "#ffffff",
                        pointBorderColor: "#4f46e5",
                        pointBorderWidth: 2.5,
                        pointRadius: 4.5,
                        pointHoverRadius: 7,
                        pointHoverBackgroundColor: "#4f46e5",
                        pointHoverBorderColor: "#ffffff",
                        pointHoverBorderWidth: 2,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: "#0f172a",
                            titleFont: { size: 12, weight: "600" },
                            bodyFont: { size: 12 },
                            padding: 10,
                            cornerRadius: 8,
                            callbacks: {
                                label: (ctx) => ` Enrolled Students: ${Number(ctx.raw).toLocaleString()}`,
                            },
                        },
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                color: "#64748b",
                                font: { size: 12, weight: "600", family: "system-ui, -apple-system, sans-serif" },
                            },
                            border: { display: false },
                        },
                        y: {
                            beginAtZero: false,
                            suggestedMin: ySuggestedMin,
                            suggestedMax: ySuggestedMax,
                            ticks: {
                                color: "#94a3b8",
                                font: { size: 11, family: "system-ui, -apple-system, sans-serif" },
                                callback: (value) => Number(value).toLocaleString(),
                            },
                            grid: {
                                color: "rgba(15, 23, 42, 0.05)",
                                drawTicks: false,
                            },
                            border: { display: false },
                        },
                    },
                },
            }));
        }

        // 2. Student Status / Program Distribution Doughnut Chart
        const targetStatusEl = this.chartStatusRef?.el || this.chartProgramRef?.el;
        if (targetStatusEl) {
            const statusData = this.state.chartData.student_status;
            const progData = this.state.chartData.program_distribution;

            const labels = statusData?.labels || progData?.labels || [];
            const dataVals = statusData?.data || progData?.data || [];
            const colors = statusData?.colors || progData?.colors || [];
            const totalCount = statusData?.total ?? this.state.dashboard?.student_count ?? 0;

            const ctxStatus = targetStatusEl.getContext("2d");

            this.charts.push(new window.Chart(ctxStatus, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [{
                        data: dataVals,
                        backgroundColor: colors,
                        borderWidth: 3,
                        borderColor: "#ffffff",
                        hoverOffset: 4,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "72%",
                    plugins: {
                        legend: { display: false },
                        centerText: {
                            label: "Total Students",
                            customValue: totalCount,
                            valueColor: "#0f172a",
                            labelColor: "#64748b",
                        },
                        tooltip: {
                            backgroundColor: "#0f172a",
                            titleFont: { size: 12, weight: "600" },
                            bodyFont: { size: 12 },
                            padding: 10,
                            cornerRadius: 8,
                            callbacks: {
                                label: (ctx) => {
                                    const val = Number(ctx.raw) || 0;
                                    const total = dataVals.reduce((a, b) => a + b, 0) || 1;
                                    const pct = Math.round((val / total) * 100);
                                    return ` ${ctx.label}: ${val.toLocaleString()} (${pct}%)`;
                                },
                            },
                        },
                    },
                },
                plugins: [doughnutCenterText],
            }));
        }
    }
}

registry.category("actions").add("school_dashboard_shell", SchoolDashboardShell);

export default SchoolDashboardShell;
