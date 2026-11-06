/** @odoo-module **/

import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { deserializeDate, deserializeDateTime, formatDate, formatDateTime } from "@web/core/l10n/dates";

const STATUS_OPTIONS = [
    { value: "present",       label: "Present",       key: "P", icon: "fa-check" },
    { value: "absent",        label: "Absent",        key: "A", icon: "fa-times" },
    { value: "late",          label: "Late",          key: "L", icon: "fa-clock-o" },
    { value: "leave",         label: "On Leave",      key: "E", icon: "fa-plane" },
    { value: "official_duty", label: "Official Duty", key: "D", icon: "fa-briefcase" },
    { value: "half_day",      label: "Half Day",      key: "H", icon: "fa-adjust" },
];

const FILTERS = [
    { value: "all",           label: "All" },
    { value: "present",       label: "Present" },
    { value: "absent",        label: "Absent" },
    { value: "late",          label: "Late" },
    { value: "leave",         label: "On Leave" },
    { value: "official_duty", label: "Official Duty" },
    { value: "half_day",      label: "Half Day" },
];

const AVATAR_TONES = 4;

function today() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function clockTime(value) {
    if (!value) return "";
    if (value instanceof Date) {
        const pad = (n) => String(n).padStart(2, "0");
        return `${pad(value.getHours())}:${pad(value.getMinutes())}`;
    }
    const match = String(value).match(/(\d{2}):(\d{2})/);
    return match ? `${match[1]}:${match[2]}` : "";
}

function utcToLocalTime(utcStr) {
    if (!utcStr) return "";
    const dateObj = new Date(utcStr.replace(" ", "T") + "Z");
    if (isNaN(dateObj.getTime())) {
        const match = String(utcStr).match(/(\d{2}):(\d{2})/);
        return match ? `${match[1]}:${match[2]}` : "";
    }
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(dateObj.getHours())}:${pad(dateObj.getMinutes())}`;
}

function localTimeToUtc(dateStr, timeStr) {
    if (!dateStr || !timeStr) return false;
    const parts = timeStr.split(":").map(Number);
    const dateParts = dateStr.split("-").map(Number);
    if (parts.length < 2 || dateParts.length < 3) return false;
    const localDate = new Date(dateParts[0], dateParts[1] - 1, dateParts[2], parts[0], parts[1], 0);
    if (isNaN(localDate.getTime())) return false;
    const pad = (n) => String(n).padStart(2, "0");
    return `${localDate.getUTCFullYear()}-${pad(localDate.getUTCMonth() + 1)}-${pad(localDate.getUTCDate())} ${pad(localDate.getUTCHours())}:${pad(localDate.getUTCMinutes())}:${pad(localDate.getUTCISeconds ? localDate.getUTCSeconds() : 0)}`;
}

function formatFloatTime(floatVal) {
    if (floatVal === undefined || floatVal === null || isNaN(floatVal)) return "08:00";
    const hours = Math.floor(floatVal);
    const minutes = Math.round((floatVal - hours) * 60);
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(hours)}:${pad(minutes)}`;
}

function initials(name) {
    const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return "?";
    const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
    return `${parts[0][0]}${last}`.toUpperCase();
}

function nameTone(name) {
    let sum = 0;
    for (const c of String(name || "")) sum += c.charCodeAt(0);
    return sum % AVATAR_TONES;
}

function fmtHours(h) {
    if (!h || h <= 0) return "-";
    const hrs = Math.floor(h);
    const mins = Math.round((h - hrs) * 60);
    if (hrs === 0) return `${mins}m`;
    return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
}

class StaffAttendanceSheet extends Component {
    static template = "school_management.StaffAttendanceSheet";
    static props = ["*"];

    setup() {
        this.orm          = useService("orm");
        this.notification = useService("notification");
        this.action       = useService("action");
        this.rootRef      = useRef("root");
        this._baseline    = "";
        this._pendingFocus = null;

        this.statusOptions = STATUS_OPTIONS;
        this.filters       = FILTERS;

        const context = this.props.action?.context || {};

        this.state = useState({
            date:                 context.default_date || context.date || today(),
            departmentId:         context.default_department_id || context.department_id || "all",
            departments:          [],
            lines:                [],
            taken:                false,
            lastSaved:            "",
            loading:              false,
            saving:               false,
            locked:               false,
            error:                null,
            query:                "",
            filter:               "all",
            activeId:             false,
            openNoteId:           false,
            isAdmin:              true,
            holidayName:          "",
            tab:                  "attendance",
            notes:                "",
            chatterRevision:      0,
            expectedCheckInTime:  "08:00",
            expectedCheckOutTime: "17:00",
            graceMinutes:         15,
            viewMode:             "table",
            isFullscreen:         false,
            // Monthly Matrix Dashboard State
            matrix:               null,
            matrixLoading:        false,
            selectedYear:         new Date().getFullYear(),
            selectedMonth:        new Date().getMonth() + 1,
            selectedDepartmentId: context.default_department_id || "all",
            selectedStaffId:      "all",
        });

        useEffect(() => {
            const sel = this._pendingFocus;
            if (!sel || !this.rootRef.el) return;
            this._pendingFocus = null;
            const node = this.rootRef.el.querySelector(sel);
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
            // Check Admin authorization
            try {
                const isSystem = Boolean(user.isAdmin || user.isSystem || (await user.hasGroup("base.group_system")));
                const isSchoolAdmin = await user.hasGroup("school_management.group_school_admin");
                this.state.isAdmin = Boolean(isSystem || isSchoolAdmin);
            } catch {
                this.state.isAdmin = Boolean(user.isAdmin || user.isSystem);
            }

            // Fetch active departments with faculty and head
            try {
                this.state.departments = await this.orm.searchRead(
                    "university.department",
                    [["active", "=", true]],
                    ["id", "name", "display_name", "faculty_id", "head_id"],
                    { order: "name asc" }
                );
            } catch (err) {
                this.state.departments = [];
            }

            // Fetch configurable policy parameters
            try {
                const params = await this.orm.searchRead(
                    "ir.config_parameter",
                    [["key", "in", [
                        "school_management.staff_expected_check_in",
                        "school_management.staff_expected_check_out",
                        "school_management.staff_late_grace_minutes",
                    ]]],
                    ["key", "value"],
                    {}
                );
                const map = {};
                for (const p of params) map[p.key] = p.value;
                if (map["school_management.staff_expected_check_in"]) {
                    this.state.expectedCheckInTime = formatFloatTime(parseFloat(map["school_management.staff_expected_check_in"]));
                }
                if (map["school_management.staff_expected_check_out"]) {
                    this.state.expectedCheckOutTime = formatFloatTime(parseFloat(map["school_management.staff_expected_check_out"]));
                }
                if (map["school_management.staff_late_grace_minutes"]) {
                    this.state.graceMinutes = parseInt(map["school_management.staff_late_grace_minutes"], 10) || 15;
                }
            } catch {
                // Keep defaults
            }

            const passedDept = context.default_department_id || context.department_id;
            if (passedDept) {
                this.state.departmentId = passedDept === "all" ? "all" : Number(passedDept);
                this.state.selectedDepartmentId = passedDept;
                await this.loadSheet();
            } else {
                this.state.departmentId = "all";
                await this.loadSheet();
            }
        });
    }

    // --- Monthly Attendance Matrix Methods ---
    async loadMatrixData() {
        this.state.matrixLoading = true;
        try {
            const data = await this.orm.call(
                "university.staff.attendance",
                "get_monthly_attendance_matrix",
                [],
                {
                    year: this.state.selectedYear,
                    month: this.state.selectedMonth,
                    department_id: this.state.selectedDepartmentId,
                    staff_id: this.state.selectedStaffId,
                }
            );
            this.state.matrix = data;
        } catch (err) {
            console.error("Failed to load monthly attendance matrix:", err);
            this.notification.add(_t("Could not load monthly attendance matrix."), { type: "danger" });
        } finally {
            this.state.matrixLoading = false;
        }
    }

    async onMatrixDepartmentChange(ev) {
        this.state.selectedDepartmentId = ev.target.value;
        await this.loadMatrixData();
    }

    async onMatrixStaffChange(ev) {
        this.state.selectedStaffId = ev.target.value;
        await this.loadMatrixData();
    }

    async onMatrixMonthChange(ev) {
        this.state.selectedMonth = parseInt(ev.target.value, 10);
        await this.loadMatrixData();
    }

    async onMatrixYearChange(ev) {
        this.state.selectedYear = parseInt(ev.target.value, 10);
        await this.loadMatrixData();
    }

    onPrint() {
        window.print();
    }

    async onMatrixCellClick(row, dayInfo) {
        if (!this.state.isAdmin) return;
        if (dayInfo.is_weekend) return; // Weekends generally not toggled by quick click

        const dStr = dayInfo.date_str;
        const cell = row.days[dStr];
        let nextStatus = "present";
        let nextHours = 9.0;

        if (cell && cell.cell_type === "worked") {
            nextStatus = "absent";
            nextHours = 0.0;
        } else if (cell && cell.cell_type === "absent") {
            nextStatus = "leave";
            nextHours = 0.0;
        } else if (cell && cell.cell_type === "leave") {
            nextStatus = "present";
            nextHours = 9.0;
        } else {
            nextStatus = "present";
            nextHours = 9.0;
        }

        try {
            await this.orm.call(
                "university.staff.attendance",
                "quick_update_attendance_cell",
                [],
                {
                    staff_id: row.id,
                    date: dStr,
                    status: nextStatus,
                    worked_hours: nextHours,
                }
            );
            await this.loadMatrixData();
            // Also refresh daily sheet if date matches
            if (this.state.date === dStr) {
                await this.loadSheet();
            }
        } catch (err) {
            console.error("Cell update error:", err);
            this.notification.add(_t("Could not update attendance cell."), { type: "danger" });
        }
    }

    // --- Derived Properties ---
    get counts() {
        const c = { present: 0, absent: 0, late: 0, leave: 0, official_duty: 0, half_day: 0, total: this.state.lines.length };
        for (const l of this.state.lines) {
            if (c[l.status] !== undefined) {
                c[l.status] += 1;
            }
        }
        return c;
    }

    get currentDepartment() {
        if (!this.state.departmentId || this.state.departmentId === "all") return null;
        return this.state.departments.find((d) => d.id === this.state.departmentId) || null;
    }

    get currentDepartmentName() {
        if (!this.state.departmentId) return "";
        if (this.state.departmentId === "all") return _t("All Departments");
        const dept = this.currentDepartment;
        return dept ? dept.display_name : "";
    }

    get currentFacultyName() {
        const dept = this.currentDepartment;
        return dept?.faculty_id ? dept.faculty_id[1] : "";
    }

    get currentHeadName() {
        const dept = this.currentDepartment;
        return dept?.head_id ? dept.head_id[1] : "";
    }

    get recordLabel() {
        if (this.state.viewMode === "dashboard") {
            const mName = this.state.matrix?.month_name || "Monthly";
            return `${mName} ${this.state.selectedYear} Matrix`;
        }
        if (!this.state.departmentId || !this.state.date) {
            return _t("Staff Attendance");
        }
        try {
            return `${this.currentDepartmentName} - ${formatDate(deserializeDate(this.state.date))}`;
        } catch {
            return `${this.currentDepartmentName} - ${this.state.date}`;
        }
    }

    get expectedHoursLabel() {
        return `${this.state.expectedCheckInTime} - ${this.state.expectedCheckOutTime}`;
    }

    get activeStaffAttendanceId() {
        if (!this.state.activeId) return false;
        const line = this.state.lines.find((l) => l.teacher_id === this.state.activeId);
        return line?.record_id || false;
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
        if (mode === "dashboard" && !this.state.matrix) {
            this.loadMatrixData();
        }
    }

    openAttendanceReport() {
        this.action.doAction("school_management.action_university_staff_attendance");
    }

    get isToday() {
        return this.state.date === today();
    }

    get timelineFormattedDate() {
        if (!this.state.date) return "";
        try {
            const parts = this.state.date.split("-").map(Number);
            const dt = new Date(parts[0], parts[1] - 1, parts[2]);
            return dt.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
        } catch {
            return this.state.date;
        }
    }

    get timelineHours() {
        return [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17];
    }

    formatHourLabel(h) {
        if (h === 12) return "12pm";
        if (h > 12) return `${h - 12}pm`;
        return `${h}am`;
    }

    isCurrentHour(h) {
        if (!this.isToday) return false;
        const nowH = new Date().getHours();
        return nowH === h;
    }

    isLinePresent(line) {
        return Boolean(line.check_in && !line.check_out) || (line.status === "present" && Boolean(line.check_in));
    }

    getLineTimeline(line) {
        if (line.status === "absent") {
            return { hasPill: false, statusText: _t("Absent"), statusClass: "o_att_pill--absent" };
        }
        if (line.status === "leave") {
            return { hasPill: false, statusText: _t("On Leave"), statusClass: "o_att_pill--leave" };
        }
        if (line.status === "official_duty") {
            return { hasPill: false, statusText: _t("Official Duty"), statusClass: "o_att_pill--duty" };
        }
        if (!line.check_in) {
            return { hasPill: false, statusText: "", statusClass: "" };
        }

        const inParts = line.check_in.split(":").map(Number);
        const startHour = (inParts[0] || 0) + (inParts[1] || 0) / 60.0;

        let endHour;
        let isOngoing = false;
        if (line.check_out) {
            const outParts = line.check_out.split(":").map(Number);
            endHour = (outParts[0] || 0) + (outParts[1] || 0) / 60.0;
            if (endHour <= startHour) endHour = startHour + 1;
        } else {
            isOngoing = true;
            const now = new Date();
            const currentHour = now.getHours() + now.getMinutes() / 60.0;
            endHour = this.isToday ? Math.max(startHour + 0.5, Math.min(18.0, currentHour)) : Math.max(startHour + 1, 17.0);
        }

        const minH = 7.0;
        const maxH = 18.0;
        const totalH = maxH - minH; // 11 hours (7:00 to 18:00)

        const clampedStart = Math.max(minH, Math.min(maxH, startHour));
        const clampedEnd = Math.max(clampedStart + 0.25, Math.min(maxH, endHour));

        const left = ((clampedStart - minH) / totalH) * 100;
        const width = Math.max(3.8, ((clampedEnd - clampedStart) / totalH) * 100);

        const format12h = (timeStr) => {
            if (!timeStr) return "";
            const [h, m] = timeStr.split(":").map(Number);
            const ampm = (h || 0) >= 12 ? "PM" : "AM";
            const h12 = (h || 0) % 12 || 12;
            const pad = (n) => String(n).padStart(2, "0");
            return `${pad(h12)}:${pad(m || 0)}:00 ${ampm}`;
        };

        let label = "";
        if (isOngoing) {
            label = `From ${format12h(line.check_in)}`;
        } else {
            const durHours = Math.floor(line.worked_hours || (endHour - startHour));
            const durMins = Math.round(((line.worked_hours || (endHour - startHour)) - durHours) * 60);
            const pad = (n) => String(n).padStart(2, "0");
            label = `${pad(durHours)}:${pad(durMins)} (${format12h(line.check_in)}-${format12h(line.check_out)})`;
        }

        return {
            hasPill: true,
            left: `${left}%`,
            width: `${width}%`,
            isOngoing,
            label,
            pillClass: isOngoing ? "o_att_pill--ongoing" : "o_att_pill--completed",
        };
    }

    onPrevDay() {
        const parts = this.state.date.split("-").map(Number);
        const d = new Date(parts[0], parts[1] - 1, parts[2]);
        d.setDate(d.getDate() - 1);
        const pad = (n) => String(n).padStart(2, "0");
        this.state.date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        this.loadSheet();
    }

    onNextDay() {
        const parts = this.state.date.split("-").map(Number);
        const d = new Date(parts[0], parts[1] - 1, parts[2]);
        d.setDate(d.getDate() + 1);
        const pad = (n) => String(n).padStart(2, "0");
        this.state.date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        this.loadSheet();
    }

    onToday() {
        this.state.date = today();
        this.loadSheet();
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.rootRef.el?.requestFullscreen().catch(() => {});
            this.state.isFullscreen = true;
        } else {
            document.exitFullscreen().catch(() => {});
            this.state.isFullscreen = false;
        }
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
        const q = this.state.query.trim().toLowerCase();
        const f = this.state.filter;
        return this.state.lines.filter((l) => {
            if (f !== "all" && l.status !== f) return false;
            if (!q) return true;
            return (
                (l.name || "").toLowerCase().includes(q) ||
                (l.code || "").toLowerCase().includes(q) ||
                (l.department || "").toLowerCase().includes(q)
            );
        });
    }

    get isDirty() {
        return this._baseline !== this.snapshot();
    }

    get isEmpty() {
        return !this.state.loading && !this.state.departmentId;
    }

    get noStaff() {
        return !this.state.loading && Boolean(this.state.departmentId) && !this.state.lines.length;
    }

    get hasNoMatch() {
        return !this.state.loading && Boolean(this.state.lines.length) && !this.visibleLines.length;
    }

    snapshot() {
        return JSON.stringify(
            this.state.lines.map((l) => [l.teacher_id, l.status, l.check_in || "", l.check_out || "", l.remark || ""])
        );
    }

    filterCount(filter) {
        const c = this.counts;
        return filter === "all" ? c.total : (c[filter] || 0);
    }

    teacherInitial(line) { return initials(line.name); }
    teacherTone(line)    { return nameTone(line.name); }
    fmtHours(h)          { return fmtHours(h); }

    getStatusBadgeClass(status) {
        if (status === "present") return "badge bg-success-subtle text-success border border-success-subtle";
        if (status === "absent") return "badge bg-danger-subtle text-danger border border-danger-subtle";
        if (status === "late") return "badge bg-warning-subtle text-warning border border-warning-subtle";
        if (status === "leave") return "badge bg-info-subtle text-info border border-info-subtle";
        if (status === "official_duty") return "badge bg-primary-subtle text-primary border border-primary-subtle";
        if (status === "half_day") return "badge bg-teal-subtle text-teal border border-teal-subtle";
        return "badge bg-secondary-subtle text-secondary border";
    }

    getStatusIconClass(status) {
        if (status === "present") return "text-success";
        if (status === "absent") return "text-danger";
        if (status === "late") return "text-warning";
        if (status === "leave") return "text-info";
        if (status === "official_duty") return "text-primary";
        if (status === "half_day") return "text-teal";
        return "text-secondary";
    }

    openTeacher(teacherId) {
        if (!teacherId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "university.teacher",
            res_id: teacherId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onNoteKeydown(line, ev) {
        if (ev.key === "Enter" || ev.key === "Escape") {
            ev.preventDefault();
            this.closeNote();
        }
    }

    // --- Data Loading ---
    async loadSheet() {
        if (!this.state.departmentId || !this.state.date) {
            this.state.lines       = [];
            this.state.taken       = false;
            this.state.lastSaved   = "";
            this.state.activeId    = false;
            this.state.holidayName = "";
            this.state.locked      = false;
            this._baseline         = this.snapshot();
            return;
        }

        this.state.loading = true;
        this.state.error   = null;

        try {
            // 1. Fetch active teachers
            const teacherDomain = [["active", "=", true]];
            if (this.state.departmentId !== "all") {
                teacherDomain.push(["department_id", "=", Number(this.state.departmentId)]);
            }

            const teachers = await this.orm.searchRead(
                "university.teacher",
                teacherDomain,
                ["id", "display_name", "teacher_id", "department_id", "image_1920"],
                { order: "name asc" }
            );

            // 2. Fetch attendance records for this date
            const attDomain = [["date", "=", this.state.date]];
            if (this.state.departmentId !== "all") {
                attDomain.push(["department_id", "=", Number(this.state.departmentId)]);
            }

            const records = await this.orm.searchRead(
                "university.staff.attendance",
                attDomain,
                ["id", "staff_id", "status", "state", "check_in", "check_out", "worked_hours", "remark", "write_date"],
                {}
            );

            // 2b. Check university holiday for this date
            try {
                const holidays = await this.orm.searchRead(
                    "university.holiday",
                    [
                        ["date_start", "<=", this.state.date],
                        ["date_end", ">=", this.state.date],
                    ],
                    ["name"],
                    { limit: 1 }
                );
                this.state.holidayName = holidays.length ? holidays[0].name : "";
            } catch {
                this.state.holidayName = "";
            }

            const recMap = {};
            let latestWrite = "";
            for (const r of records) {
                recMap[r.staff_id[0]] = r;
                if (r.write_date && (!latestWrite || r.write_date > latestWrite)) {
                    latestWrite = r.write_date;
                }
            }

            this.state.taken = records.length > 0;
            this.state.lastSaved = latestWrite ? clockTime(latestWrite) : (this.state.taken ? _t("Earlier") : "");

            // 3. Assemble staff rows
            this.state.lines = teachers.map((t) => {
                const rec = recMap[t.id] || null;
                const checkIn  = rec ? utcToLocalTime(rec.check_in) : this.state.expectedCheckInTime;
                const checkOut = rec ? utcToLocalTime(rec.check_out) : this.state.expectedCheckOutTime;
                return {
                    teacher_id:   t.id,
                    record_id:    rec?.id || false,
                    name:         t.display_name,
                    code:         t.teacher_id || "",
                    department:   t.department_id ? t.department_id[1] : "",
                    has_image:    Boolean(t.image_1920),
                    status:       rec?.status || "present",
                    state:        rec?.state || "draft",
                    check_in:     checkIn,
                    check_out:    checkOut,
                    worked_hours: rec?.worked_hours || 0,
                    remark:       rec?.remark || "",
                    is_new:       !rec,
                };
            });

            this.state.activeId = this.state.lines.length ? this.state.lines[0].teacher_id : false;
            this.state.openNoteId = false;
            this.state.locked = false;
            this._baseline = this.snapshot();
        } catch (e) {
            this.state.error = e.message || _t("Unable to load staff attendance.");
        } finally {
            this.state.loading = false;
        }
    }

    // --- Header Controls ---
    async onDepartmentChange(ev) {
        const val = ev.target.value;
        this.state.departmentId = val === "all" ? "all" : (Number(val) || "");
        await this.loadSheet();
    }

    async onDateChange(ev) {
        this.state.date = ev.target.value;
        await this.loadSheet();
    }

    onSearchInput(ev) { this.state.query = ev.target.value; }
    setFilter(v) { this.state.filter = v; }
    clearFilters() { this.state.query = ""; this.state.filter = "all"; }
    setActive(line) { this.state.activeId = line.teacher_id; }

    // --- Status Controls ---
    setStatus(line, status) {
        if (!this.state.isAdmin || this.state.locked) return;
        this.state.activeId = line.teacher_id;
        line.status = status;
        if (status === "absent" || status === "leave") {
            line.check_in     = "";
            line.check_out    = "";
            line.worked_hours = 0;
        } else if (status === "half_day") {
            line.check_in = this.state.expectedCheckInTime;
            line.check_out = this._addMinutes(line.check_in, 240);
            this._recalcHours(line);
        } else if (status === "present" || status === "official_duty") {
            line.check_in = this.state.expectedCheckInTime;
            line.check_out = this.state.expectedCheckOutTime;
            this._recalcHours(line);
        }
    }

    markAllPresent() {
        if (!this.state.isAdmin || this.state.locked) return;
        for (const l of this.state.lines) {
            l.status = "present";
            l.check_in = this.state.expectedCheckInTime;
            l.check_out = this.state.expectedCheckOutTime;
            this._recalcHours(l);
        }
    }

    // --- Time & Hours ---
    onCheckInChange(line, ev) {
        if (!this.state.isAdmin || this.state.locked) return;
        line.check_in = ev.target.value;
        this._applyLateStatus(line);
        this._recalcHours(line);
    }

    onCheckOutChange(line, ev) {
        if (!this.state.isAdmin || this.state.locked) return;
        line.check_out = ev.target.value;
        this._recalcHours(line);
    }

    _addMinutes(value, minutes) {
        const [hours, mins] = String(value || "08:00").split(":").map(Number);
        const total = hours * 60 + mins + minutes;
        return `${String(Math.floor(total / 60) % 24).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
    }

    _applyLateStatus(line) {
        if (!line.check_in || !["present", "late"].includes(line.status)) return;
        const [hours, mins] = line.check_in.split(":").map(Number);
        const [startHours, startMins] = this.state.expectedCheckInTime.split(":").map(Number);
        line.status = hours * 60 + mins > startHours * 60 + startMins + this.state.graceMinutes ? "late" : "present";
    }

    _recalcHours(line) {
        if (line.check_in && line.check_out) {
            const [h1, m1] = line.check_in.split(":").map(Number);
            const [h2, m2] = line.check_out.split(":").map(Number);
            const mins = (h2 * 60 + m2) - (h1 * 60 + m1);
            line.worked_hours = mins > 0 ? Number((mins / 60).toFixed(2)) : 0;
        } else {
            line.worked_hours = 0;
        }
    }

    // --- Notes ---
    toggleNote(line) {
        const isOpen = this.state.openNoteId === line.teacher_id;
        this.state.activeId   = line.teacher_id;
        this.state.openNoteId = isOpen ? false : line.teacher_id;
        this._pendingFocus    = isOpen ? null : ".o_att_note_input";
    }

    closeNote() { this.state.openNoteId = false; }
    updateNote(line, ev) { if (this.state.isAdmin) line.remark = ev.target.value; }
    clearNote(line)  { if (this.state.isAdmin) line.remark = ""; }

    // --- Keyboard Navigation ---
    onGlobalKeydown(ev) {
        const tag = (ev.target.tagName || "").toLowerCase();
        if (["input", "textarea", "select"].includes(tag) || ev.target.isContentEditable) return;
        if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
        if (this.state.saving || this.state.loading || !this.state.lines.length) return;

        if (ev.key === "Escape" && this.state.openNoteId) {
            ev.preventDefault();
            this.closeNote();
            return;
        }

        const visible = this.visibleLines;
        if (!visible.length) return;
        let idx = visible.findIndex((l) => l.teacher_id === this.state.activeId);
        if (idx < 0) idx = 0;

        if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
            ev.preventDefault();
            const next = ev.key === "ArrowDown" ? idx + 1 : idx - 1;
            this.state.activeId = visible[Math.min(Math.max(next, 0), visible.length - 1)].teacher_id;
            return;
        }

        if (!this.state.isAdmin) return;

        const opt = this.statusOptions.find((o) => o.key.toLowerCase() === ev.key.toLowerCase());
        if (!opt) return;
        ev.preventDefault();
        this.setStatus(visible[idx], opt.value);
        if (idx < visible.length - 1) {
            this.state.activeId = visible[idx + 1].teacher_id;
        }
    }

    // --- Save Attendance ---
    async saveAttendance() {
        if (!this.state.isAdmin || this.state.locked) {
            this.notification.add(_t("Only administrators can record staff attendance."), { type: "danger" });
            return;
        }
        if (!this.state.departmentId || !this.state.date || !this.state.lines.length) return;

        // Front-end validation: check-out must be strictly after check-in
        for (const line of this.state.lines) {
            if (line.check_in && line.check_out && line.check_out <= line.check_in) {
                this.state.error = _t("Check-out must be after check-in for %(name)s.", { name: line.name });
                this.notification.add(this.state.error, { type: "danger" });
                return;
            }
        }

        this.state.saving = true;
        this.state.error  = null;

        try {
            const toCreate = [];
            const toWrite  = [];

            for (const line of this.state.lines) {
                // If record is already approved, it is locked against modification
                if (line.record_id && line.state === "approved") {
                    continue;
                }

                const checkIn  = localTimeToUtc(this.state.date, line.check_in);
                const checkOut = localTimeToUtc(this.state.date, line.check_out);

                const vals = {
                    staff_id:  line.teacher_id,
                    date:      this.state.date,
                    status:    line.status,
                    check_in:  checkIn,
                    check_out: checkOut,
                    remark:    line.remark || "",
                };

                if (line.record_id) {
                    toWrite.push([line.record_id, vals]);
                } else {
                    vals.state = "draft";
                    toCreate.push(vals);
                }
            }

            if (toCreate.length) {
                await this.orm.create("university.staff.attendance", toCreate);
            }
            for (const [id, vals] of toWrite) {
                await this.orm.write("university.staff.attendance", [id], vals);
            }

            await this.loadSheet();
            this.state.lastSaved = clockTime(new Date());
            this.state.locked = true;

            const c = this.counts;
            const deptLabel = this.currentDepartmentName;
            const summaryParts = [
                `${c.total} staff`,
                `${c.present} present`,
                `${c.absent} absent`,
                `${c.late} late`,
                `${c.leave} on leave`,
            ];
            if (c.official_duty > 0) summaryParts.push(`${c.official_duty} official duty`);
            if (c.half_day > 0) summaryParts.push(`${c.half_day} half day`);
            this.notification.add(
                deptLabel ? _t("Attendance saved for %(dept)s", { dept: deptLabel }) : _t("Staff attendance saved"),
                {
                    type: "success",
                    message: summaryParts.join(" • "),
                }
            );
        } catch (e) {
            this.state.error = e.message || _t("Unable to save attendance.");
            this.notification.add(this.state.error, { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    onBack() {
        if (this.env.config?.historyBack) {
            this.env.config.historyBack();
        } else {
            this.action.doAction("school_management.action_university_staff_attendance");
        }
    }
}

registry.category("actions").add("university_staff_attendance_sheet", StaffAttendanceSheet);
export default StaffAttendanceSheet;
