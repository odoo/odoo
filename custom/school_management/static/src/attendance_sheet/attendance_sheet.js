/** @odoo-module **/

import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { deserializeDate, deserializeDateTime, formatDate, formatDateTime } from "@web/core/l10n/dates";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const STATUS_OPTIONS = [
    { value: "present", label: "Present", key: "P" },
    { value: "absent",  label: "Absent",  key: "A" },
    { value: "late",    label: "Late",    key: "L" },
    { value: "excused", label: "Excused", key: "E" },
];

const FILTERS = [
    { value: "all",     label: "All" },
    { value: "present", label: "Present" },
    { value: "absent",  label: "Absent" },
    { value: "late",    label: "Late" },
    { value: "excused", label: "Excused" },
];

/** Column metadata for the schedule-style agenda kanban (mirrors university_schedule). */
const KANBAN_STATUS_GROUPS = [
    { key: "present", label: "Present", badgeClass: "badge text-bg-success" },
    { key: "late",    label: "Late",    badgeClass: "badge text-bg-warning" },
    { key: "absent",  label: "Absent",  badgeClass: "badge text-bg-danger" },
    { key: "excused", label: "Excused", badgeClass: "badge text-bg-secondary" },
];

const AVATAR_TONES = 4;

function today() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function clockTime(value) {
    if (!value) {
        return "";
    }
    return formatDateTime(deserializeDateTime(value), { format: "HH:mm" });
}

function initials(name) {
    const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
    if (!parts.length) {
        return "?";
    }
    const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
    return `${parts[0][0]}${last}`.toUpperCase();
}

function nameTone(name) {
    let sum = 0;
    for (const character of String(name || "")) {
        sum += character.charCodeAt(0);
    }
    return sum % AVATAR_TONES;
}

export class AttendanceSheet extends Component {
    static template = "school_management.AttendanceSheet";
    static components = { Chatter };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialog = useService("dialog");
        const context = this.props.action?.context || {};

        this.statusOptions = STATUS_OPTIONS;
        this.filters = FILTERS;
        this.rootRef = useRef("root");
        this._baseline = "";
        this._pendingFocus = null;

        this.state = useState({
            date: context.default_date || context.date || today(),
            sectionId: Number(context.default_section_id || context.section_id || 0) || 0,
            departmentId: context.default_department_id || "all",
            departments: [],
            sections: [],
            lines: [],
            taken: false,
            lastSaved: "",
            loading: false,
            saving: false,
            error: null,
            query: "",
            filter: "all",
            // Student attendance is intentionally card-based.  Keep this in state so
            // the existing template remains reactive without exposing a second layout.
            viewMode: "kanban",
            activeId: false,
            openNoteId: false,
            session: {},
            notes: "",
            tab: "attendance",
            chatterRevision: 0,
            isAdmin: true,
        });

        // Restore DOM focus after a re-render so keyboard flows are not broken.
        useEffect(() => {
            const selector = this._pendingFocus;
            if (!selector || !this.rootRef.el) {
                return;
            }
            this._pendingFocus = null;
            const node = this.rootRef.el.querySelector(selector);
            if (node) {
                node.focus();
                if (node.type === "text") {
                    node.setSelectionRange(node.value.length, node.value.length);
                }
            }
        });

        this._onKeydown = (ev) => this.onGlobalKeydown(ev);
        document.addEventListener("keydown", this._onKeydown);
        onWillUnmount(() => document.removeEventListener("keydown", this._onKeydown));

        onWillStart(async () => {
            try {
                const isSystem = Boolean(user.isAdmin || user.isSystem || (await user.hasGroup("base.group_system")));
                const isSchoolAdmin = await user.hasGroup("school_management.group_school_admin");
                this.state.isAdmin = Boolean(isSystem || isSchoolAdmin);
            } catch {
                this.state.isAdmin = Boolean(user.isAdmin || user.isSystem);
            }

            await this.loadSections();
            const passedId = Number(context.default_section_id || context.section_id || 0) || 0;
            if (passedId && this.state.sections.some((s) => s.id === passedId)) {
                this.state.sectionId = passedId;
            } else {
                const available = this.filteredSections;
                this.state.sectionId = available.length ? available[0].id : 0;
            }
            if (this.state.sectionId) {
                await this.loadSheet();
            }
        });
    }

    // ------------------------------------------------------------------
    // Derived data
    // ------------------------------------------------------------------
    get counts() {
        const counts = { present: 0, absent: 0, late: 0, excused: 0, total: this.state.lines.length };
        for (const line of this.state.lines) {
            counts[line.status] = (counts[line.status] || 0) + 1;
        }
        return counts;
    }

    get filteredSections() {
        if (!this.state.departmentId || this.state.departmentId === "all") {
            return this.state.sections;
        }
        const deptId = Number(this.state.departmentId);
        return this.state.sections.filter((s) => s.department_id && s.department_id[0] === deptId);
    }

    get currentSectionName() {
        const sec = this.state.sections.find((s) => s.id === this.state.sectionId);
        return sec ? sec.display_name : "";
    }

    get recordLabel() {
        if (!this.state.sectionId || !this.state.date) {
            return _t("New attendance session");
        }
        return `${this.currentSectionName} - ${formatDate(deserializeDate(this.state.date))}`;
    }

    formatSessionTime(value) {
        return value ? formatDateTime(deserializeDateTime(value)) : "";
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    getStatusBadgeClass(status) {
        // Pill classes aligned with Scheduled Sessions status badges
        if (status === "present") return "badge text-bg-success";
        if (status === "absent") return "badge text-bg-danger";
        if (status === "late") return "badge text-bg-warning";
        return "badge text-bg-secondary";
    }

    getStatusIconClass(status) {
        if (status === "present") return "text-success";
        if (status === "absent") return "text-danger";
        if (status === "late") return "text-warning";
        return "text-secondary";
    }

    onTabKeydown(ev) {
        if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(ev.key)) {
            ev.preventDefault();
            this.state.tab = ev.key === "Home" ? "attendance" : ev.key === "End" ? "details" :
                this.state.tab === "attendance" ? "details" : "attendance";
            this._pendingFocus = `[role="tab"][data-tab="${this.state.tab}"]`;
        }
    }

    get visibleLines() {
        const query = this.state.query.trim().toLowerCase();
        if (!query && this.state.filter === "all") {
            return this.state.lines;
        }
        return this.state.lines.filter((line) => {
            if (this.state.filter !== "all" && line.status !== this.state.filter) {
                return false;
            }
            if (!query) {
                return true;
            }
            return (
                (line.name || "").toLowerCase().includes(query) ||
                (line.code || "").toLowerCase().includes(query)
            );
        });
    }

    /**
     * Status columns for the agenda kanban — same grouping pattern as
     * Scheduled Sessions (university_schedule.kanbanGroups).
     */
    get kanbanGroups() {
        const lines = this.visibleLines;
        return KANBAN_STATUS_GROUPS.map((meta) => ({
            ...meta,
            lines: lines.filter((line) => line.status === meta.key),
        })).filter((group) => group.lines.length > 0 || this.state.filter === "all");
    }

    get attendanceRate() {
        const tally = this.counts;
        if (!tally.total) {
            return 0;
        }
        return Math.round(((tally.present + tally.late) / tally.total) * 100);
    }

    get activeStudent() {
        const visible = this.visibleLines;
        return visible.find((line) => line.student_id === this.state.activeId) || visible[0] || null;
    }

    setViewMode(mode) {
        this.state.viewMode = mode === "list" ? "list" : "kanban";
    }

    statusPercent(status) {
        const tally = this.counts;
        if (!tally.total) {
            return 0;
        }
        return Math.round(((tally[status] || 0) / tally.total) * 100);
    }

    get isDirty() {
        return this._baseline !== this.snapshot();
    }

    get isEmpty() {
        return !this.state.loading && !this.state.sectionId && !this.state.lines.length;
    }

    get noStudents() {
        return (
            !this.state.loading &&
            Boolean(this.state.sectionId) &&
            !this.state.lines.length
        );
    }

    get hasNoMatch() {
        return !this.state.loading && Boolean(this.state.lines.length) && !this.visibleLines.length;
    }

    snapshot() {
        return JSON.stringify(
            [this.state.notes, this.state.lines.map((line) => [line.student_id, line.status, line.remark || ""])]
        );
    }

    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------
    async loadSections() {
        try {
            this.state.departments = await this.orm.searchRead(
                "university.department",
                [["active", "=", true]],
                ["id", "name", "display_name"],
                { order: "name asc" }
            );

            this.state.sections = await this.orm.call(
                "university.attendance",
                "get_available_sections",
                []
            );
        } catch (error) {
            this.state.error = error.message || _t("Unable to load sections.");
        }
    }

    applySheet(sheet) {
        this.state.lines = sheet.lines || [];
        this.state.session = sheet.session || sheet || {};
        this.state.notes = this.state.session.notes || sheet.notes || "";
        this.state.taken = Boolean(sheet.taken);
        this.state.lastSaved = clockTime(sheet.last_saved || sheet.last_saved_at || sheet.saved_at);
        this.state.activeId = this.state.lines.length ? this.state.lines[0].student_id : false;
        this.state.openNoteId = false;
        this.state.chatterRevision += 1;
        this._baseline = this.snapshot();
    }

    async loadSheet() {
        if (!this.state.sectionId) {
            this.state.lines = [];
            this.state.session = {};
            this.state.taken = false;
            this.state.lastSaved = "";
            this._baseline = this.snapshot();
            return;
        }
        this.state.loading = true;
        this.state.error = null;
        try {
            const sheet = await this.orm.call("university.attendance", "get_section_attendance_sheet", [
                this.state.sectionId,
                this.state.date,
            ]);
            this.applySheet(sheet);
        } catch (error) {
            this.state.error = error.message || _t("Unable to load attendance.");
            this.state.taken = false;
            this.state.lastSaved = "";
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------
    // Header controls
    // ------------------------------------------------------------------
    async confirmDiscard() {
        if (!this.isDirty) {
            return true;
        }
        return new Promise((resolve) => this.dialog.add(ConfirmationDialog, {
            body: _t("Discard the unsaved attendance and session notes?"),
            confirm: () => resolve(true),
            cancel: () => resolve(false),
        }, { onClose: () => resolve(false) }));
    }

    async onBack() {
        if (!await this.confirmDiscard()) {
            return;
        }
        if (this.env.config?.historyBack) {
            this.env.config.historyBack();
        } else {
            this.action.doAction("school_management.action_university_attendance");
        }
    }

    onPrint() {
        window.print();
    }

    openAttendanceReport() {
        this.action.doAction("school_management.action_university_attendance");
    }

    openStudent(studentId) {
        if (!studentId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "university.student",
            res_id: studentId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onDateChange(ev) {
        if (!ev.target.value || !await this.confirmDiscard()) {
            ev.target.value = this.state.date;
            return;
        }
        this.state.date = ev.target.value;
        await this.loadSheet();
    }

    async onPrevDay() {
        if (!await this.confirmDiscard()) return;
        const parts = this.state.date.split("-").map(Number);
        const d = new Date(parts[0], parts[1] - 1, parts[2]);
        d.setDate(d.getDate() - 1);
        const pad = (n) => String(n).padStart(2, "0");
        this.state.date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        await this.loadSheet();
    }

    async onNextDay() {
        if (!await this.confirmDiscard()) return;
        const parts = this.state.date.split("-").map(Number);
        const d = new Date(parts[0], parts[1] - 1, parts[2]);
        d.setDate(d.getDate() + 1);
        const pad = (n) => String(n).padStart(2, "0");
        this.state.date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        await this.loadSheet();
    }

    async onToday() {
        if (!await this.confirmDiscard()) return;
        this.state.date = today();
        await this.loadSheet();
    }

    async onDepartmentFilterChange(ev) {
        if (!await this.confirmDiscard()) {
            ev.target.value = this.state.departmentId;
            return;
        }
        this.state.departmentId = ev.target.value;
        const available = this.filteredSections;
        if (available.length && !available.some((s) => s.id === this.state.sectionId)) {
            this.state.sectionId = available[0].id;
            await this.loadSheet();
        } else if (!available.length) {
            this.state.sectionId = 0;
            await this.loadSheet();
        }
    }

    async onSectionChange(ev) {
        if (!await this.confirmDiscard()) {
            ev.target.value = this.state.sectionId;
            return;
        }
        this.state.sectionId = Number(ev.target.value) || 0;
        await this.loadSheet();
    }

    // ------------------------------------------------------------------
    // Toolbar
    // ------------------------------------------------------------------
    onSearchInput(ev) {
        this.state.query = ev.target.value;
    }

    setFilter(value) {
        this.state.filter = value;
    }

    filterCount(filter) {
        const counts = this.counts;
        if (filter === "all") {
            return counts.total;
        }
        return counts[filter] || 0;
    }

    // ------------------------------------------------------------------
    // Attendance selection
    // ------------------------------------------------------------------
    setStatus(line, status) {
        if (this.state.loading || this.state.saving) {
            return;
        }
        this.state.activeId = line.student_id;
        if (line.status !== status) {
            line.status = status;
        }
    }

    setActive(line) {
        this.state.activeId = line.student_id;
    }

    onCardKeyDown(line, ev) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this.setActive(line);
        }
    }

    markAllPresent() {
        for (const line of this.state.lines) {
            line.status = "present";
        }
    }

    studentInitial(line) {
        return initials(line.name);
    }

    studentTone(line) {
        return nameTone(line.name);
    }

    studentImageUrl(line) {
        const field = line.image_field || "image_1920";
        return `/web/image/${line.student_model || "university.student"}/${line.student_id}/${field}`;
    }

    // ------------------------------------------------------------------
    // Notes
    // ------------------------------------------------------------------
    toggleRemark(line) {
        const isOpen = this.state.openNoteId === line.student_id;
        this.state.activeId = line.student_id;
        this.state.openNoteId = isOpen ? false : line.student_id;
        this._pendingFocus = isOpen ? null : ".o_att_note_input";
    }

    closeRemark() {
        this.state.openNoteId = false;
    }

    updateRemark(line, ev) {
        line.remark = ev.target.value;
    }

    clearRemark(line) {
        line.remark = "";
        this._pendingFocus = ".o_att_note_input";
    }

    onNoteKeydown(line, ev) {
        if (ev.key === "Enter" || ev.key === "Escape") {
            ev.preventDefault();
            ev.stopPropagation();
            this.closeRemark();
        }
    }

    // ------------------------------------------------------------------
    // Keyboard
    // ------------------------------------------------------------------
    statusButtonSelector(studentId, status) {
        return `.o_att_seg__btn[data-student="${studentId}"][data-status="${status}"]`;
    }

    onSegKeydown(line, ev) {
        if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        const current = this.statusOptions.findIndex(
            (option) => option.value === ev.target.dataset.status
        );
        const step = ev.key === "ArrowRight" ? 1 : -1;
        const next = this.statusOptions[(current + step + this.statusOptions.length) % this.statusOptions.length];
        this.setStatus(line, next.value);
        this._pendingFocus = this.statusButtonSelector(line.student_id, next.value);
    }

    focusDescriptor() {
        const active = this.rootRef.el ? this.rootRef.el.ownerDocument.activeElement : null;
        if (!active || !this.rootRef.el || !this.rootRef.el.contains(active)) {
            return null;
        }
        if (active.classList.contains("o_att_seg__btn")) {
            return this.statusButtonSelector(active.dataset.student, active.dataset.status);
        }
        if (active.classList.contains("o_att_note_input")) {
            return ".o_att_note_input";
        }
        return null;
    }

    onGlobalKeydown(ev) {
        const target = ev.target;
        if (this.state.tab !== "attendance" || !this.rootRef.el?.contains(target) || target.closest(".o_att_chatter")) {
            return;
        }
        if (target.matches("input, textarea, select")) {
            return;
        }
        if (["ArrowDown", "ArrowUp", "j", "k"].includes(ev.key)) {
            ev.preventDefault();
            const visible = this.visibleLines;
            if (!visible.length) {
                return;
            }
            const currentIndex = visible.findIndex((line) => line.student_id === this.state.activeId);
            const delta = ["ArrowDown", "j"].includes(ev.key) ? 1 : -1;
            const nextIndex = Math.max(0, Math.min(visible.length - 1, currentIndex + delta));
            const nextLine = visible[nextIndex];
            this.state.activeId = nextLine.student_id;
            this._pendingFocus = this.statusButtonSelector(nextLine.student_id, nextLine.status);
            return;
        }
        if (["p", "a", "l", "e"].includes(ev.key.toLowerCase())) {
            const current = this.activeStudent;
            if (!current) {
                return;
            }
            const map = { p: "present", a: "absent", l: "late", e: "excused" };
            this.setStatus(current, map[ev.key.toLowerCase()]);
            this._pendingFocus = this.statusButtonSelector(current.student_id, map[ev.key.toLowerCase()]);
        }
    }

    // ------------------------------------------------------------------
    // Save
    // ------------------------------------------------------------------
    async saveAttendance() {
        if (!this.state.sectionId) {
            return;
        }
        this.state.saving = true;
        this.state.error = null;
        try {
            const linesPayload = this.state.lines.map((line) => ({
                student_id: line.student_id,
                status: line.status,
                remark: line.remark || "",
            }));

            const result = await this.orm.call("university.attendance", "save_section_attendance", [
                this.state.sectionId,
                this.state.date,
                linesPayload,
                this.state.notes,
            ]);

            this.state.taken = true;
            this.state.lastSaved = clockTime(result.saved_at || result.last_saved || result.last_saved_at);
            const sessionId = result.session_id || result.session?.id || result.session?.session_id;
            if (sessionId) {
                this.state.session.session_id = sessionId;
            }
            this._baseline = this.snapshot();
            this.notification.add(_t("Attendance saved successfully."), { type: "success" });
        } catch (error) {
            this.state.error = error.message || _t("Failed to save attendance.");
            this.notification.add(this.state.error, { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }
}

registry.category("actions").add("university_attendance_sheet", AttendanceSheet);

export { AttendanceSheet };
