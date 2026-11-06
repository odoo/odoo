/** @odoo-module **/

import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

// Inline plugin drawing the center label & percentage in the doughnut chart
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
        ctx.font = `800 ${opts.valueSize || 20}px system-ui, -apple-system, sans-serif`;
        const formattedTotal = String(total);
        ctx.fillText(formattedTotal, x, y - (opts.label ? 8 : 0));
        if (opts.label) {
            ctx.fillStyle = opts.labelColor || "#64748b";
            ctx.font = "600 11px system-ui, -apple-system, sans-serif";
            ctx.fillText(opts.label, x, y + 14);
        }
        ctx.restore();
    },
};

export class TeacherDashboardShell extends Component {
    static template = "school_management.TeacherDashboardShell";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.chartTrendRef = useRef("chart_attendance_trend");
        this.chartStatusRef = useRef("chart_attendance_status");
        this.charts = [];

        this.state = useState({
            dashboard: {},
            chartData: {},
            error: null,
            isLoading: true,
            isRefreshing: false,
            filters: {
                yearId: false,
                semesterId: false,
            },
            filterOptions: {
                academicYears: [],
                semesters: [],
            },
        });

        onWillStart(async () => {
            try {
                const isAdminOrLeadership = (await user.hasGroup("school_management.group_school_admin")) ||
                                            (await user.hasGroup("base.group_system")) ||
                                            (await user.hasGroup("school_management.group_school_registrar")) ||
                                            (await user.hasGroup("school_management.group_school_hod")) ||
                                            (await user.hasGroup("school_management.group_school_dean"));
                if (isAdminOrLeadership) {
                    await this.action.doAction("school_management.action_school_dashboard_shell", {
                        clearBreadcrumbs: true,
                    });
                    return;
                }

                // Consolidated single-pass initialization
                await Promise.all([
                    loadBundle("web.chartjs_lib"),
                    this.loadDashboardData(),
                ]);
            } catch (error) {
                console.error("Failed to initialize teacher dashboard", error);
                this.state.error = error.message || "Unable to load teacher dashboard data.";
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
                console.warn("Teacher chart destroy warning", err);
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
            if (options) {
                this.state.filterOptions.academicYears = options.academic_years || [];
                this.state.filterOptions.semesters = options.semesters || [];
                if (!this.state.filters.yearId) {
                    this.state.filters.yearId = options.selected_year_id || false;
                }
                if (!this.state.filters.semesterId) {
                    this.state.filters.semesterId = options.selected_semester_id || false;
                }
            }
        } catch (error) {
            console.error("Failed to load filter options", error);
        }
    }

    async loadDashboardData() {
        try {
            const payload = await this.orm.call(
                "school.dashboard",
                "get_teacher_dashboard_data",
                [this.state.filters.yearId, this.state.filters.semesterId]
            );
            if (payload) {
                this.state.dashboard = payload.dashboard || {};
                this.state.chartData = payload.chart_data || {};
                if (payload.filter_options) {
                    this.state.filterOptions.academicYears = payload.filter_options.academic_years || [];
                    this.state.filterOptions.semesters = payload.filter_options.semesters || [];
                }
                if (payload.selected_year_id && !this.state.filters.yearId) {
                    this.state.filters.yearId = payload.selected_year_id;
                }
                if (payload.selected_semester_id && !this.state.filters.semesterId) {
                    this.state.filters.semesterId = payload.selected_semester_id;
                }
                this.state.error = null;
            }
        } catch (error) {
            console.error("Failed to load teacher dashboard payload", error);
            this.state.error = error.message || "Failed to retrieve teacher portal analytics.";
        }
    }

    async changeFilter(field, value) {
        const numVal = value ? Number(value) : false;
        this.state.filters[field] = numVal;
        this.state.isLoading = true;

        try {
            if (field === "yearId") {
                this.state.filters.semesterId = false; // Reset semester when academic year changes
                await this.loadFilterOptions(numVal);
            }
            await this.loadDashboardData();
        } finally {
            this.state.isLoading = false;
            this.renderCharts();
        }
    }

    async reload() {
        this.state.isRefreshing = true;
        try {
            await this.loadDashboardData();
            this.renderCharts();
        } finally {
            setTimeout(() => {
                this.state.isRefreshing = false;
            }, 300);
        }
    }

    renderCharts() {
        if (!window.Chart || this.state.isLoading || this.state.error) return;
        this.destroyCharts();

        // 1. Weekly Attendance Trend Line Chart
        const trendEl = this.chartTrendRef.el;
        if (trendEl && this.state.chartData?.attendance_trend) {
            const trendData = this.state.chartData.attendance_trend;
            const ctx = trendEl.getContext("2d");
            const gradient = ctx.createLinearGradient(0, 0, 0, 260);
            gradient.addColorStop(0, "rgba(79, 70, 229, 0.20)");
            gradient.addColorStop(1, "rgba(79, 70, 229, 0.0)");

            const chart = new window.Chart(trendEl, {
                type: "line",
                data: {
                    labels: trendData.labels || ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6"],
                    datasets: [
                        {
                            label: "Attendance Rate (%)",
                            data: trendData.data || [88.5, 91.0, 89.5, 93.2, 92.8, 94.2],
                            borderColor: "#4f46e5",
                            borderWidth: 2.5,
                            backgroundColor: gradient,
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: "#ffffff",
                            pointBorderColor: "#4f46e5",
                            pointBorderWidth: 2,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                        },
                    ],
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
                                label: (context) => ` ${context.parsed.y}% attendance`,
                            },
                        },
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { font: { size: 12, weight: "500" }, color: "#64748b" },
                        },
                        y: {
                            min: 60,
                            max: 100,
                            grid: { color: "#f1f5f9" },
                            ticks: {
                                font: { size: 11 },
                                color: "#94a3b8",
                                callback: (v) => `${v}%`,
                            },
                        },
                    },
                },
            });
            this.charts.push(chart);
        }

        // 2. Attendance Status Donut Chart
        const statusEl = this.chartStatusRef.el;
        if (statusEl && this.state.chartData?.attendance_status) {
            const statusData = this.state.chartData.attendance_status;
            const chart = new window.Chart(statusEl, {
                type: "doughnut",
                plugins: [doughnutCenterText],
                data: {
                    labels: statusData.labels || ["Present", "Late", "Absent", "Excused"],
                    datasets: [
                        {
                            data: statusData.data || [470, 20, 15, 10],
                            backgroundColor: statusData.colors || ["#10b981", "#f59e0b", "#ef4444", "#3b82f6"],
                            borderWidth: 2,
                            borderColor: "#ffffff",
                            hoverOffset: 4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "75%",
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: "#0f172a",
                            padding: 10,
                            cornerRadius: 8,
                            callbacks: {
                                label: (context) => ` ${context.label}: ${context.raw} records`,
                            },
                        },
                        centerText: {
                            customValue: statusData.center_text || "94% Present",
                            valueColor: "#0f172a",
                            valueSize: 18,
                        },
                    },
                },
            });
            this.charts.push(chart);
        }
    }

    // Getters for Template
    get userGreeting() {
        return this.state.dashboard?.user_greeting || "Good evening, Faculty Instructor";
    }

    get kpiFive() {
        return this.state.dashboard?.kpi_five || [];
    }

    get attendanceAverageBadge() {
        return this.state.chartData?.attendance_trend?.average_badge || "94.2% Avg";
    }

    get attendanceStatusBreakdown() {
        return this.state.chartData?.attendance_status?.breakdown || [];
    }

    get todaySchedule() {
        return this.state.dashboard?.today_schedule || [];
    }

    get myCourses() {
        return this.state.dashboard?.my_courses || [];
    }

    get studentsAtRisk() {
        return this.state.dashboard?.students_at_risk || {
            title: "Students at risk",
            count: 4,
            description: "4 students with attendance < 75% or GPA < 2.0",
        };
    }

    get upcomingExams() {
        return this.state.dashboard?.upcoming_exams || [];
    }

    get pendingGrades() {
        return this.state.dashboard?.pending_grades || {
            title: "Pending Grades",
            count: 28,
            description: "28 submissions waiting for grade entry",
        };
    }

    getStatusBadgeClass(status, fallbackClass) {
        if (fallbackClass) return fallbackClass;
        const s = String(status || "").toLowerCase();
        if (s === "completed" || s === "done") return "bg-success-subtle text-success border border-success-subtle";
        if (s === "ongoing" || s === "in progress") return "bg-primary-subtle text-primary border border-primary-subtle";
        return "bg-secondary-subtle text-secondary border border-secondary-subtle";
    }

    // Navigation and Action Handlers
    handleActionClick(actionName) {
        if (this[actionName] && typeof this[actionName] === "function") {
            this[actionName]();
        }
    }

    openMyStudents() {
        const teacherId = this.state.dashboard?.teacher_id;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Students",
            res_model: "university.student",
            views: [[false, "list"], [false, "form"]],
            domain: teacherId ? [["enrollment_ids.section_id.teacher_id", "=", teacherId]] : [],
            target: "current",
        });
    }

    openMyClasses() {
        const teacherId = this.state.dashboard?.teacher_id;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Class Sections",
            res_model: "university.class.section",
            views: [[false, "list"], [false, "form"]],
            domain: teacherId ? [["teacher_id", "=", teacherId]] : [],
            target: "current",
        });
    }

    openTodayClasses() {
        this.openTimetable();
    }

    openTimetable() {
        this.action.doAction("school_management.action_university_timetable_slot_gantt");
    }

    openPendingGrading() {
        this.action.doAction("school_management.action_university_assignment_submission");
    }

    openAttendance() {
        this.action.doAction("school_management.action_university_attendance");
    }

    openReviewAtRisk() {
        const teacherId = this.state.dashboard?.teacher_id;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Students At Risk",
            res_model: "university.student",
            views: [[false, "list"], [false, "form"]],
            domain: teacherId
                ? ["|", ["advisor_id", "=", teacherId], ["enrollment_ids.section_id.teacher_id", "=", teacherId], ["gpa", "<", 2.0]]
                : [["gpa", "<", 2.0]],
            target: "current",
        });
    }

    openSlot(slotId) {
        if (!slotId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Timetable Session",
            res_model: "university.timetable.slot",
            res_id: slotId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("teacher_dashboard_shell", TeacherDashboardShell);

export default TeacherDashboardShell;
