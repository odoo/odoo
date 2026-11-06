/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

function pad(value) {
    return String(value).padStart(2, "0");
}

function localToday() {
    const today = new Date();
    return { year: today.getFullYear(), month: today.getMonth() + 1 };
}

export class AttendanceGrid extends Component {
    static template = "school_management.AttendanceGrid";
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
            grid: null,
            statuses: [],
            savingCell: false,
            viewMode: "kanban", // "kanban" or "matrix"
            selectedSectionId: "all",
            searchQuery: "",
        });

        onWillStart(async () => {
            try {
                const options = await this.orm.call(
                    "university.attendance",
                    "get_attendance_options",
                    []
                );
                this.state.statuses = options.statuses;
            } catch (error) {
                this.state.statuses = [
                    { value: "present", label: "Present", key: "P" },
                    { value: "absent", label: "Absent", key: "A" },
                    { value: "late", label: "Late", key: "L" },
                    { value: "excused", label: "Excused", key: "E" },
                ];
            }
            await this.load();
        });
    }

    async load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const grid = await this.orm.call(
                "university.attendance",
                "get_grid_data",
                [[], this.state.month, this.state.year]
            );
            this.state.grid = grid;
        } catch (error) {
            this.state.error = error.message || String(error);
        } finally {
            this.state.loading = false;
        }
    }

    async onMonthChange(event) {
        this.state.month = Number(event.target.value);
        await this.load();
    }

    async onYearChange(event) {
        this.state.year = Number(event.target.value);
        await this.load();
    }

    onSectionFilterChange(event) {
        this.state.selectedSectionId = event.target.value;
    }

    onSearchInput(event) {
        this.state.searchQuery = (event.target.value || "").trim().toLowerCase();
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    openSectionMatrix(sectionId) {
        this.state.selectedSectionId = String(sectionId);
        this.state.viewMode = "matrix";
    }

    openAttendanceSheet(sectionId) {
        this.action.doAction("school_management.action_university_attendance_session", {
            additionalContext: {
                default_section_id: sectionId,
                section_id: sectionId,
            },
        });
    }

    openTakeAttendance(sectionId) {
        this.action.doAction("school_management.action_university_attendance_take_wizard", {
            additionalContext: {
                default_section_id: sectionId,
            },
        });
    }

    openPrintWizard(sectionId = null) {
        const context = {};
        if (sectionId) {
            context.default_section_ids = [sectionId];
        } else if (this.state.selectedSectionId !== "all") {
            context.default_section_ids = [Number(this.state.selectedSectionId)];
        }
        this.action.doAction("school_management.action_university_attendance_print_wizard", {
            additionalContext: context,
        });
    }

    async refresh() {
        await this.load();
    }

    async onCellChange(sectionId, studentId, day, ev) {
        const status = ev.target.value;
        await this.updateCell(sectionId, studentId, day, status);
    }

    async updateCell(sectionId, studentId, day, status) {
        if (this.state.savingCell) {
            return;
        }
        if (!status) {
            return;
        }
        this.state.savingCell = true;
        try {
            const date = `${this.state.year}-${pad(this.state.month)}-${pad(day)}`;
            await this.orm.call(
                "university.attendance",
                "update_cell",
                [sectionId, studentId, date, status]
            );
            this.notification.add(_t("Attendance updated"), { type: "success" });
            await this.load();
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        } finally {
            this.state.savingCell = false;
        }
    }

    studentCounts(student) {
        const counts = { present: 0, absent: 0, late: 0, excused: 0 };
        for (const cell of student.cells || []) {
            if (cell.status in counts) {
                counts[cell.status] += 1;
            }
        }
        return counts;
    }

    rate(student) {
        let total = 0;
        let credited = 0;
        for (const cell of student.cells || []) {
            if (!cell.status) {
                continue;
            }
            total += 1;
            if (cell.status !== "absent") {
                credited += 1;
            }
        }
        return total ? Math.round((credited * 1000) / total) / 10 : 100;
    }

    isRisk(student, threshold) {
        const total = (student.cells || []).filter((cell) => cell.status).length;
        return total >= 3 && this.rate(student) < threshold;
    }

    sectionRate(section) {
        let total = 0;
        let credited = 0;
        for (const student of section.students || []) {
            for (const cell of student.cells || []) {
                if (cell.status) {
                    total++;
                    if (cell.status !== "absent") {
                        credited++;
                    }
                }
            }
        }
        return total ? Math.round((credited * 1000) / total) / 10 : 100;
    }

    sectionAtRiskCount(section, threshold) {
        const th = threshold || (this.state.grid ? this.state.grid.threshold : 75);
        return (section.students || []).filter((s) => this.isRisk(s, th)).length;
    }

    sectionTotalLogs(section) {
        let count = 0;
        for (const student of section.students || []) {
            for (const cell of student.cells || []) {
                if (cell.status) {
                    count++;
                }
            }
        }
        return count;
    }

    getHealthBadgeClass(rate) {
        if (rate >= 90) return "badge bg-success-subtle text-success border border-success-subtle";
        if (rate >= 75) return "badge bg-warning-subtle text-warning border border-warning-subtle";
        return "badge bg-danger-subtle text-danger border border-danger-subtle";
    }

    getHealthLabel(rate) {
        if (rate >= 90) return _t("Excellent");
        if (rate >= 75) return _t("Good");
        return _t("Attention Needed");
    }

    getProgressBarClass(rate) {
        if (rate >= 90) return "bg-success";
        if (rate >= 75) return "bg-warning";
        return "bg-danger";
    }

    get summary() {
        if (!this.state.grid || !this.state.grid.sections) {
            return { totalSections: 0, totalStudents: 0, avgRate: 0, totalAtRisk: 0 };
        }
        const sections = this.state.grid.sections;
        const totalSections = sections.length;
        let totalStudents = 0;
        let rateSum = 0;
        let totalAtRisk = 0;
        const threshold = this.state.grid.threshold || 75;

        for (const section of sections) {
            totalStudents += (section.students || []).length;
            rateSum += this.sectionRate(section);
            totalAtRisk += this.sectionAtRiskCount(section, threshold);
        }

        const avgRate = totalSections ? Math.round((rateSum / totalSections) * 10) / 10 : 0;
        return { totalSections, totalStudents, avgRate, totalAtRisk };
    }

    get filteredSections() {
        if (!this.state.grid || !this.state.grid.sections) {
            return [];
        }
        let list = this.state.grid.sections;
        if (this.state.selectedSectionId !== "all") {
            list = list.filter((s) => String(s.id) === String(this.state.selectedSectionId));
        }
        if (this.state.searchQuery) {
            const q = this.state.searchQuery;
            list = list.filter((s) => {
                const name = (s.name || "").toLowerCase();
                const dName = (s.display_name || "").toLowerCase();
                const subj = (s.subject || "").toLowerCase();
                const teacher = (s.teacher || "").toLowerCase();
                const dept = (s.department || "").toLowerCase();
                return name.includes(q) || dName.includes(q) || subj.includes(q) || teacher.includes(q) || dept.includes(q);
            });
        }
        return list;
    }
}

registry.category("actions").add("university_attendance_grid", AttendanceGrid);

export { AttendanceGrid };
