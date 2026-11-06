/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

function localToday() {
    return new Date().getFullYear();
}

export class AttendanceComparison extends Component {
    static template = "school_management.AttendanceComparison";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            year: localToday(),
            loading: true,
            error: null,
            data: null,
            viewMode: "kanban", // "kanban" or "table"
            facultyFilter: "all",
            departmentFilter: "all",
            statusFilter: "all", // "all", "good", "warn", "bad"
            searchQuery: "",
            expandedSections: {},
        });

        onWillStart(async () => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.orm.call(
                "university.attendance",
                "get_comparison_data",
                [this.state.year]
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

    onPrint() {
        window.print();
    }

    clearSearch() {
        this.state.searchQuery = "";
    }

    async onYearChange(event) {
        this.state.year = Number(event.target.value);
        await this.load();
    }

    onFacultyFilterChange(event) {
        this.state.facultyFilter = event.target.value;
        this.state.departmentFilter = "all";
    }

    toggleFacultyFilter(facultyId) {
        const targetId = String(facultyId);
        if (this.state.facultyFilter === targetId) {
            this.state.facultyFilter = "all";
        } else {
            this.state.facultyFilter = targetId;
        }
        this.state.departmentFilter = "all";
    }

    onDepartmentFilterChange(event) {
        this.state.departmentFilter = event.target.value;
    }

    onSearchInput(event) {
        this.state.searchQuery = (event.target.value || "").trim().toLowerCase();
    }

    setStatusFilter(status) {
        this.state.statusFilter = status;
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    toggleSectionStudents(sectionId) {
        this.state.expandedSections[sectionId] = !this.state.expandedSections[sectionId];
    }

    openSectionSheet(sectionId) {
        this.action.doAction("school_management.action_university_attendance_session", {
            additionalContext: {
                default_section_id: sectionId,
                section_id: sectionId,
            },
        });
    }

    openSectionGrid(sectionId) {
        this.action.doAction("school_management.action_university_attendance_grid", {
            additionalContext: {
                section_id: sectionId,
            },
        });
    }

    openStudent(studentId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "university.student",
            res_id: studentId,
            views: [[false, "form"]],
        });
    }

    getRateStatus(rate) {
        if (rate >= 90) return "good";
        if (rate >= 75) return "warn";
        return "bad";
    }

    getRateStatusLabel(rate) {
        if (rate >= 90) return _t("Excellent");
        if (rate >= 75) return _t("Average");
        return _t("At Risk");
    }

    getRateBadgeClass(rate) {
        if (rate >= 90) return "badge bg-success-subtle text-success border border-success-subtle flex-shrink-0 text-nowrap";
        if (rate >= 75) return "badge bg-warning-subtle text-warning border border-warning-subtle flex-shrink-0 text-nowrap";
        return "badge bg-danger-subtle text-danger border border-danger-subtle flex-shrink-0 text-nowrap";
    }

    getRateProgressBarClass(rate) {
        if (rate >= 90) return "bg-success";
        if (rate >= 75) return "bg-warning";
        return "bg-danger";
    }

    get currentTimeStr() {
        const d = new Date();
        const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const month = months[d.getMonth()];
        const day = String(d.getDate()).padStart(2, "0");
        let hours = d.getHours();
        const minutes = String(d.getMinutes()).padStart(2, "0");
        const ampm = hours >= 12 ? "PM" : "AM";
        hours = hours % 12;
        hours = hours ? hours : 12;
        const hoursStr = String(hours).padStart(2, "0");
        return `${month} ${day} ${hoursStr}:${minutes} ${ampm}`;
    }

    get reportDate() {
        const d = new Date();
        return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
    }

    get faculties() {
        return (this.state.data && this.state.data.faculties) || [];
    }

    get availableDepartments() {
        if (!this.state.data || !this.state.data.departments) {
            return [];
        }
        if (this.state.facultyFilter === "all") {
            return this.state.data.departments;
        }
        return this.state.data.departments.filter(
            (dept) => String(dept.faculty_id) === String(this.state.facultyFilter)
        );
    }

    get summary() {
        if (!this.state.data || !this.state.data.departments) {
            return {
                totalFaculties: 0,
                totalDepts: 0,
                totalSections: 0,
                totalRecords: 0,
                avgRate: 0,
                goodCount: 0,
                warnCount: 0,
                badCount: 0,
            };
        }
        const totalFaculties = this.faculties.length;
        const totalDepts = this.state.data.departments.length;
        let totalSections = 0;
        let totalRecords = 0;
        let rateSum = 0;
        let rateCount = 0;
        let goodCount = 0;
        let warnCount = 0;
        let badCount = 0;

        for (const dept of this.state.data.departments) {
            const sections = dept.sections || [];
            totalSections += sections.length;
            totalRecords += (dept.total || 0);
            if (typeof dept.rate === "number") {
                rateSum += dept.rate;
                rateCount++;
            }
            for (const s of sections) {
                const st = this.getRateStatus(s.rate);
                if (st === "good") goodCount++;
                else if (st === "warn") warnCount++;
                else badCount++;
            }
        }
        const avgRate = rateCount ? Math.round((rateSum / rateCount) * 10) / 10 : 0;
        return { totalFaculties, totalDepts, totalSections, totalRecords, avgRate, goodCount, warnCount, badCount };
    }

    get filteredDepartments() {
        if (!this.state.data || !this.state.data.departments) {
            return [];
        }
        const query = this.state.searchQuery;
        return this.state.data.departments
            .filter((dept) => {
                if (this.state.facultyFilter !== "all" && String(dept.faculty_id) !== String(this.state.facultyFilter)) {
                    return false;
                }
                if (this.state.departmentFilter !== "all" && String(dept.id) !== String(this.state.departmentFilter)) {
                    return false;
                }
                return true;
            })
            .map((dept) => {
                let sections = dept.sections || [];
                if (this.state.statusFilter !== "all") {
                    sections = sections.filter((s) => {
                        const status = this.getRateStatus(s.rate);
                        return status === this.state.statusFilter;
                    });
                }
                if (query) {
                    const deptMatches = (dept.name || "").toLowerCase().includes(query) ||
                                        (dept.faculty_name || "").toLowerCase().includes(query) ||
                                        (dept.faculty_code || "").toLowerCase().includes(query);
                    if (!deptMatches) {
                        sections = sections.filter((s) =>
                            (s.name || "").toLowerCase().includes(query)
                        );
                    }
                }
                return {
                    ...dept,
                    filteredSections: sections,
                };
            })
            .filter((dept) => dept.filteredSections.length > 0 || !query);
    }
}

registry.category("actions").add("university_attendance_comparison", AttendanceComparison);

export { AttendanceComparison };
