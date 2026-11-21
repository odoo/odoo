/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

function localToday() {
    const today = new Date();
    return { year: today.getFullYear(), month: today.getMonth() + 1 };
}

export class AttendanceAtRisk extends Component {
    static template = "school_management.AttendanceAtRisk";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        const today = localToday();
        this.state = useState({
            month: today.month,
            year: today.year,
            loading: true,
            error: null,
            data: null,
            viewMode: "kanban", // "kanban" or "table"
            severityFilter: "all", // "all", "critical", "moderate"
            departmentFilter: "all",
            searchQuery: "",
        });

        onWillStart(async () => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.orm.call(
                "university.attendance",
                "get_at_risk_data",
                [this.state.month, this.state.year, []]
            );
            this.state.data = data;
        } catch (error) {
            this.state.error = error.message || String(error);
        } finally {
            this.state.loading = false;
        }
    }

    onBack() {
        this.action.doAction("school_management.action_university_attendance");
    }

    async onMonthChange(event) {
        this.state.month = Number(event.target.value);
        await this.load();
    }

    async onYearChange(event) {
        this.state.year = Number(event.target.value);
        await this.load();
    }

    onDepartmentFilterChange(event) {
        this.state.departmentFilter = event.target.value;
    }

    onSearchInput(event) {
        this.state.searchQuery = (event.target.value || "").trim().toLowerCase();
    }

    clearSearch() {
        this.state.searchQuery = "";
    }

    setSeverityFilter(severity) {
        this.state.severityFilter = severity;
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    async refresh() {
        await this.load();
    }

    rateLabel(student) {
        return `${student.rate}%`;
    }

    barWidth(student) {
        return `${Math.min(Math.max(Math.round(student.rate), 2), 100)}%`;
    }

    isCritical(student) {
        return student.rate < 50;
    }

    getRiskBadgeClass(rate) {
        if (rate < 50) {
            return "badge bg-danger-subtle text-danger border border-danger-subtle";
        }
        return "badge bg-warning-subtle text-warning border border-warning-subtle";
    }

    getRiskLabel(rate) {
        if (rate < 50) {
            return _t("Critical Risk");
        }
        return _t("At Risk");
    }

    getProgressBarClass(rate) {
        if (rate < 50) {
            return "bg-danger";
        }
        return "bg-warning";
    }

    openStudent(studentId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "university.student",
            res_id: studentId,
            views: [[false, "form"]],
        });
    }

    openAttendance(studentId, studentName) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `${studentName} - Attendance History`,
            res_model: "university.attendance",
            domain: [["student_id", "=", studentId]],
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });
    }

    get summary() {
        if (!this.state.data || !this.state.data.students) {
            return {
                totalAtRisk: 0,
                criticalCount: 0,
                moderateCount: 0,
                avgRate: 0,
                threshold: 75,
                criticalPct: 0,
                moderatePct: 0,
            };
        }
        const students = this.state.data.students;
        const totalAtRisk = students.length;
        const criticalCount = students.filter((s) => s.rate < 50).length;
        const moderateCount = students.filter((s) => s.rate >= 50).length;
        const rateSum = students.reduce((acc, s) => acc + (s.rate || 0), 0);
        const avgRate = totalAtRisk ? Math.round((rateSum / totalAtRisk) * 10) / 10 : 0;
        const threshold = this.state.data.threshold || 75;
        const criticalPct = totalAtRisk ? Math.round((criticalCount / totalAtRisk) * 100) : 0;
        const moderatePct = totalAtRisk ? Math.round((moderateCount / totalAtRisk) * 100) : 0;
        return { totalAtRisk, criticalCount, moderateCount, avgRate, threshold, criticalPct, moderatePct };
    }

    get departments() {
        if (!this.state.data || !this.state.data.students) {
            return [];
        }
        const depts = new Set();
        for (const s of this.state.data.students) {
            if (s.department) {
                depts.add(s.department);
            }
        }
        return Array.from(depts).sort();
    }

    get filteredStudents() {
        if (!this.state.data || !this.state.data.students) {
            return [];
        }
        let list = this.state.data.students;
        if (this.state.severityFilter === "critical") {
            list = list.filter((s) => s.rate < 50);
        } else if (this.state.severityFilter === "moderate") {
            list = list.filter((s) => s.rate >= 50);
        }

        if (this.state.departmentFilter !== "all") {
            list = list.filter((s) => s.department === this.state.departmentFilter);
        }

        if (this.state.searchQuery) {
            const q = this.state.searchQuery;
            list = list.filter((s) => {
                const name = (s.name || "").toLowerCase();
                const code = (s.code || "").toLowerCase();
                const dept = (s.department || "").toLowerCase();
                const program = (s.program || "").toLowerCase();
                return name.includes(q) || code.includes(q) || dept.includes(q) || program.includes(q);
            });
        }
        return list;
    }

    get criticalStudents() {
        return this.filteredStudents.filter((s) => s.rate < 50);
    }

    get moderateStudents() {
        return this.filteredStudents.filter((s) => s.rate >= 50);
    }
}

registry.category("actions").add("university_attendance_at_risk", AttendanceAtRisk);

export { AttendanceAtRisk };
