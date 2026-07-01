import { Component, onWillStart, proxy } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { Time } from "@web/core/l10n/time";
import { rpc, ConnectionLostError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { formatFloatTime } from "@web/views/fields/formatters";
import { parseFloatTime } from "@web/views/fields/parsers";
import { TimePicker } from "@web/core/time_picker/time_picker";
import { useService } from "@web/core/utils/hooks";
import { isIosApp } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { AttendanceVideoStream } from "@hr_attendance/components/attendance_video_stream/attendance_video_stream";
import { BreakDurationDialog } from "@hr_attendance/components/break_duration_dialog/break_duration_dialog";

export class ActivityMenu extends Component {
    static components = { Dropdown, DropdownItem, TimePicker, AttendanceVideoStream };
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.lazySession = useService("lazy_session");
        this.notification = useService("notification");
        this.state = proxy({
            employee: null,
            todayAttendanceRecords: [],
            checkedIn: false,
            isDisplayed: false,
            captureCheckInImage: false,
            streamAvailable: null,
            activeAttendanceId: null,
            editingAttendanceId: null,
            savingAttendance: false,
            editDraft: {
                checkIn: null,
                checkOut: null,
                breakDuration: "0",
            },
        });

        this.cameraCapture = null;
        this.dropdown = useDropdownState();

        onWillStart(() => {
            this.lazySession.getValue("attendance_user_data", (employee) => {
                if (employee) {
                    this.state.employee = employee;
                    this.attendanceCheckInPermission = employee.has_attendance_check_in_ability;
                    this._searchReadEmployeeFill();
                }
            });
        });
    }

    async searchReadEmployee() {
        this.state.employee = await rpc("/hr_attendance/attendance_user_data");
        this.attendanceCheckInPermission =
            this.state.employee?.has_attendance_check_in_ability ?? false;
        this._searchReadEmployeeFill();
    }

    _searchReadEmployeeFill() {
        if (!this.state.employee?.id) {
            this.state.isDisplayed = false;
            this.state.todayAttendanceRecords = [];
            return;
        }

        this.state.isDisplayed = this.attendanceCheckInPermission;
        this.state.checkedIn = this.state.employee.attendance_state === "checked_in";
        this.state.captureCheckInImage =
            this.state.employee.capture_check_in_image && !this.state.checkedIn;

        this.state.todayAttendanceRecords = [...(this.state.employee.today_attendance_ids || [])].sort(
            (attendanceA, attendanceB) =>
                deserializeDateTime(attendanceA.check_in).ts -
                deserializeDateTime(attendanceB.check_in).ts
        );

        const fallbackAttendanceId =
            this.state.employee.last_attendance?.id || this.state.todayAttendanceRecords.at(-1)?.id || null;
        if (!this._getAttendanceById(this.state.activeAttendanceId)) {
            this.state.activeAttendanceId = fallbackAttendanceId;
        }
        if (this.state.editingAttendanceId && !this._getAttendanceById(this.state.editingAttendanceId)) {
            this.cancelInlineEdit();
        }

    }
    get todayAttendanceSessions() {
        return this._buildAttendanceSessions();
    }

    get attendanceDetails() {
        return this._buildAttendanceReview(this._getAttendanceById(this.state.activeAttendanceId));
    }

    get hasCheckedInToday() {
        return this.todayAttendanceSessions.length > 0;
    }

    _buildAttendanceSessions() {
        return this.state.todayAttendanceRecords.map((att) => {
            const checkInDate = deserializeDateTime(att.check_in);
            const checkOutDate = att.check_out ? deserializeDateTime(att.check_out) : null;
            const duration = att.check_out ? att.worked_hours : this.state.employee.last_attendance_worked_hours;
            return {
                id: att.id,
                canEdit: Boolean(att.can_edit),
                selected: att.id === this.state.activeAttendanceId,
                rangeLabel: `${this._formatAttendanceTime(checkInDate)} - ${
                    checkOutDate ? this._formatAttendanceTime(checkOutDate) : _t("Now")
                }`,
                durationLabel: this._formatCompactDuration(duration),
            };
        });
    }

    _getAttendanceById(attendanceId) {
        if (!attendanceId) {
            return this.state.employee?.last_attendance || null;
        }
        return (
            this.state.todayAttendanceRecords.find((attendance) => attendance.id === attendanceId) ||
            (this.state.employee?.last_attendance?.id === attendanceId ? this.state.employee.last_attendance : null)
        );
    }

    setCameraCapture(capturePicture) {
        this.cameraCapture = capturePicture;
    }

    setStreamAvailable(isAvailable) {
        this.state.streamAvailable = isAvailable;
    }

    get showVideoStream() {
        return this.state.captureCheckInImage && this.state.streamAvailable !== false;
    }

    beforeDropdownOpen() {
        this.setStreamAvailable(null);
        return this.searchReadEmployee();
    }

    _buildAttendanceReview(attendance) {
        if (!(attendance && attendance.check_in)) {
            return null;
        }
        const checkIn = deserializeDateTime(attendance.check_in);
        const checkOut = attendance.check_out ? deserializeDateTime(attendance.check_out) : null;
        const daySummary = this._getReviewSummary(attendance);
        return {
            id: attendance.id,
            canEdit: Boolean(attendance.can_edit),
            dateLabel: this._formatAttendanceDateLabel(checkIn, checkOut),
            entries: [
                {
                    key: "check_in",
                    label: _t("Check In"),
                    time: this._formatAttendanceTime(checkIn),
                    location: attendance.in_location || false,
                    pending: false,
                },
                {
                    key: "check_out",
                    label: _t("Check Out"),
                    time: checkOut ? this._formatAttendanceTime(checkOut) : _t("Pending"),
                    location: checkOut ? attendance.out_location || false : false,
                    pending: !checkOut,
                },
            ],
            showBreakSummary: Boolean(this.state.employee.break_management_enabled),
            breakDisplay: formatFloatTime(daySummary.breakDuration, { numeric: true }),
            totalDisplay: formatFloatTime(daySummary.workedHours, { numeric: true }),
            sessions: this.todayAttendanceSessions,
        };
    }

    _formatAttendanceDateLabel(checkIn, checkOut) {
        const options = {
            weekday: "long",
            day: "numeric",
            month: "short",
        };
        const startLabel = checkIn.toLocaleString(options);
        if (!(checkOut && !checkIn.hasSame(checkOut, "day"))) {
            return startLabel;
        }
        return `${startLabel} - ${checkOut.toLocaleString(options)}`;
    }

    _formatAttendanceTime(dateTime) {
        return dateTime.toLocaleString({
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    _formatCompactDuration(duration) {
        return formatFloatTime(duration || 0, { numeric: true }).replace(":", "h");
    }

    _parseDateTimeInputValue(value) {
        return value?.isValid ? value : null;
    }

    _getAttendanceFieldDateTime(attendance, fieldName) {
        const attendanceField = fieldName === "checkIn" ? "check_in" : "check_out";
        return attendance?.[attendanceField] ? deserializeDateTime(attendance[attendanceField]) : null;
    }

    _getInlineTimeValue(dateTime) {
        const value = this._parseDateTimeInputValue(dateTime);
        return value ? new Time(value.toObject()) : null;
    }

    _getInlineEditBaseDate(fieldName) {
        const currentDraftValue = this._parseDateTimeInputValue(this.state.editDraft[fieldName]);
        if (currentDraftValue) {
            return currentDraftValue;
        }
        const attendance = this._getAttendanceById(this.state.editingAttendanceId);
        const attendanceValue = this._getAttendanceFieldDateTime(attendance, fieldName);
        if (attendanceValue) {
            return attendanceValue;
        }
        if (fieldName === "checkOut") {
            return (
                this._parseDateTimeInputValue(this.state.editDraft.checkIn) ||
                this._getAttendanceFieldDateTime(attendance, "checkIn")
            );
        }
        return null;
    }

    _formatBreakDurationInputValue(durationHours) {
        return formatFloatTime(Math.max(durationHours || 0, 0));
    }

    _parseBreakDurationInputValue(durationValue) {
        return Math.max(parseFloatTime(durationValue) || 0, 0);
    }

    _getAttendanceMetrics(attendance, { includeDraft = false } = {}) {
        const isEditingAttendance = includeDraft && attendance.id === this.state.editingAttendanceId;
        if (isEditingAttendance) {
            const checkInDate = this._parseDateTimeInputValue(this.state.editDraft.checkIn);
            const checkOutDate = this._parseDateTimeInputValue(this.state.editDraft.checkOut);
            if (checkInDate?.isValid) {
                const breakDuration = checkOutDate?.isValid
                    ? this._parseBreakDurationInputValue(this.state.editDraft.breakDuration)
                    : 0;
                const endDate = checkOutDate?.isValid ? checkOutDate : luxon.DateTime.now();
                const workedHours = Math.max(endDate.diff(checkInDate, "minutes").minutes / 60 - breakDuration, 0);
                return {
                    breakDuration,
                    workedHours,
                };
            }
        }
        return {
            breakDuration: attendance.check_out ? attendance.break_duration || 0 : 0,
            workedHours: attendance.check_out
                ? attendance.worked_hours || 0
                : this.state.employee.last_attendance_worked_hours || 0,
        };
    }

    _getAttendanceDaySummary({ includeDraft = false } = {}) {
        return this.state.todayAttendanceRecords.reduce(
            (summary, attendance) => {
                const metrics = this._getAttendanceMetrics(attendance, { includeDraft });
                summary.breakDuration += metrics.breakDuration;
                summary.workedHours += metrics.workedHours;
                return summary;
            },
            { breakDuration: 0, workedHours: 0 }
        );
    }

    _getReviewSummary(attendance, { includeDraft = false } = {}) {
        if (!attendance) {
            return { breakDuration: 0, workedHours: 0 };
        }
        if (this.state.todayAttendanceRecords.some((todayAttendance) => todayAttendance.id === attendance.id)) {
            return this._getAttendanceDaySummary({ includeDraft });
        }
        return this._getAttendanceMetrics(attendance, { includeDraft });
    }

    _serializeDateTimeInputValue(inputValue) {
        const dateTime = this._parseDateTimeInputValue(inputValue);
        if (!dateTime) {
            return false;
        }
        return serializeDateTime(dateTime.set({ second: 0, millisecond: 0 }));
    }

    _getInlineEditErrorMessage(error) {
        return error?.data?.message || error?.message || _t("Could not update this attendance.");
    }

    updateInlineDateTimeDraft(fieldName, value) {
        if (fieldName) {
            const baseDate = this._getInlineEditBaseDate(fieldName);
            const timeValue = Time.from(value);
            let nextDateTime = baseDate && timeValue ? baseDate.set(timeValue.toObject()) : null;
            if (fieldName === "checkOut" && nextDateTime) {
                const originalCheckOut = this._getAttendanceFieldDateTime(
                    this._getAttendanceById(this.state.editingAttendanceId),
                    "checkOut"
                );
                const checkInDateTime = this._parseDateTimeInputValue(this.state.editDraft.checkIn);
                if (!originalCheckOut && checkInDateTime && nextDateTime < checkInDateTime) {
                    nextDateTime = nextDateTime.plus({ days: 1 });
                }
            }
            this.state.editDraft[fieldName] = nextDateTime;
        }
    }

    openAttendanceForm(attendanceId) {
        const attendance = this._getAttendanceById(attendanceId);
        if (!attendance) {
            return;
        }
        if (this.state.editingAttendanceId) {
            this.notification.add(_t("Save or cancel your attendance changes before opening another record."), {
                title: _t("Attendance Review"),
                type: "warning",
            });
            return;
        }
        this.state.activeAttendanceId = attendance.id;
        this.dropdown.close();
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.attendance",
            res_id: attendance.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    selectAttendance(attendanceId) {
        if (this.state.editingAttendanceId) {
            this.startInlineEdit(attendanceId);
            return;
        }
        this.openAttendanceForm(attendanceId);
    }

    isEditing(attendanceDetails) {
        return Boolean(
            attendanceDetails &&
                this.state.editingAttendanceId === attendanceDetails.id
        );
    }

    startInlineEdit(attendanceId = this.state.activeAttendanceId) {
        const attendance = this._getAttendanceById(attendanceId);
        if (!(attendance && attendance.can_edit)) {
            return;
        }
        this.state.activeAttendanceId = attendance.id;
        this.state.editingAttendanceId = attendance.id;
        this.state.editDraft.checkIn = deserializeDateTime(attendance.check_in);
        this.state.editDraft.checkOut = attendance.check_out ? deserializeDateTime(attendance.check_out) : null;
        this.state.editDraft.breakDuration = this._formatBreakDurationInputValue(
            attendance.break_duration || 0
        );
    }

    cancelInlineEdit() {
        this.state.editingAttendanceId = null;
        this.state.savingAttendance = false;
        if (!this.state.activeAttendanceId && this.state.employee?.last_attendance?.id) {
            this.state.activeAttendanceId = this.state.employee.last_attendance.id;
        }
    }

    breakDisplay(attendanceDetails) {
        if (!this.isEditing(attendanceDetails)) {
            return attendanceDetails.breakDisplay;
        }
        const attendance = this._getAttendanceById(attendanceDetails.id);
        return formatFloatTime(
            this._getReviewSummary(attendance, { includeDraft: true }).breakDuration,
            { numeric: true }
        );
    }

    totalDisplay(attendanceDetails) {
        if (!this.isEditing(attendanceDetails)) {
            return attendanceDetails.totalDisplay;
        }
        const attendance = this._getAttendanceById(attendanceDetails.id);
        return formatFloatTime(
            this._getReviewSummary(attendance, { includeDraft: true }).workedHours,
            { numeric: true }
        );
    }

    async saveInlineEdit() {
        const attendanceId = this.state.editingAttendanceId;
        if (!attendanceId || this.state.savingAttendance) {
            return;
        }
        if (!this._parseDateTimeInputValue(this.state.editDraft.checkIn)) {
            this.notification.add(_t("Check-in is required."), {
                title: _t("Attendance Error"),
                type: "danger",
            });
            return;
        }
        this.state.savingAttendance = true;
        try {
            const vals = {
                check_in: this._serializeDateTimeInputValue(this.state.editDraft.checkIn),
                check_out: this.state.editDraft.checkOut
                    ? this._serializeDateTimeInputValue(this.state.editDraft.checkOut)
                    : false,
                break_duration: this.state.editDraft.checkOut
                    ? this._parseBreakDurationInputValue(this.state.editDraft.breakDuration)
                    : 0,
            };
            await this.orm.write("hr.attendance", [attendanceId], vals);
            this.state.editingAttendanceId = null;
            await this.searchReadEmployee();
        } catch (error) {
            this.notification.add(this._getInlineEditErrorMessage(error), {
                title: _t("Attendance Error"),
                type: "danger",
            });
        } finally {
            this.state.savingAttendance = false;
        }
    }
    async checking(latitude = false, longitude = false, breakDurationHours = null, checkInImage = null) {
        try {
            this.state.employee = await rpc("/hr_attendance/systray_check_in_out", {
                latitude,
                longitude,
                break_duration: breakDurationHours,
                check_in_image: checkInImage,
            });
            this._searchReadEmployeeFill();
            if (this.state.employee?.notification?.message) {
                this.notification.add(this.state.employee.notification.message, {
                    type: this.state.employee.notification.type,
                });
            }
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.notification.add(_t("Connection lost. Check in/out could not be recorded."), {
                    title: _t("Attendance Error"),
                    type: "danger",
                    sticky: false,
                });
            } else {
                throw error;
            }
        } finally {
            this._attendanceInProgress = false;
        }
    }

    confirmChecking(breakDurationHours = null, checkInImage = null) {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Unable to get a valid location. Do you want to proceed with your check-in/out anyway?"),
            confirmLabel: _t("Proceed Anyway"),
            confirm: async () => await this.checking(false, false, breakDurationHours, checkInImage),
            cancel: () => (this._attendanceInProgress = false),
        });
    }

    get closeSystrayOnCheckIn() {
        return true;
    }

    async signInOut() {
        const checkInImage = this.state.captureCheckInImage ? this.cameraCapture?.() : null;
        if (this.closeSystrayOnCheckIn) {
            this.dropdown.close();
        }
        if (this._attendanceInProgress) {
            return;
        }
        this._attendanceInProgress = true;

        try {
            await this.searchReadEmployee();
            if (!this.state.employee || !this.state.employee.id) {
                this._attendanceInProgress = false;
                return;
            }
            let breakDurationHours = null;
            if (this.state.employee.break_management_enabled && this.state.employee.attendance_state === "checked_in") {
                const minutes = await this.requestBreakDuration(this._getCurrentAttendanceMaxBreakMinutes());
                if (minutes === null) {
                    this._attendanceInProgress = false;
                    return;
                }
                breakDurationHours = (Number(minutes) || 0) / 60;
            }
            const trackingEnabled = this.state.employee && this.state.employee.device_tracking_enabled;
            if (trackingEnabled && !isIosApp() && navigator.geolocation && navigator.onLine) {
                navigator.geolocation.getCurrentPosition(
                    async ({ coords: { latitude, longitude } }) => {
                        await this.checking(latitude, longitude, breakDurationHours, checkInImage);
                    },
                    () => {
                        this.confirmChecking(breakDurationHours, checkInImage);
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                    }
                );
            } else if (trackingEnabled) {
                this.confirmChecking(breakDurationHours, checkInImage);
            } else {
                await this.checking(false, false, breakDurationHours, checkInImage);
            }
        } catch (error) {
            this._attendanceInProgress = false;
            throw error;
        }
    }

    _getCurrentAttendanceMaxBreakMinutes() {
        const attendance = this.state.employee?.last_attendance;
        if (!attendance?.check_in) {
            return null;
        }
        const checkInDate = deserializeDateTime(attendance.check_in);
        const checkOutDate = attendance.check_out
            ? deserializeDateTime(attendance.check_out)
            : luxon.DateTime.now();
        if (!(checkInDate?.isValid && checkOutDate?.isValid)) {
            return null;
        }
        const durationMinutes = checkOutDate.diff(checkInDate, "minutes").minutes;
        return Math.max(Math.floor(durationMinutes || 0), 0);
    }

    async requestBreakDuration(maxMinutes = null) {
        return new Promise((resolve) => {
            let settled = false;
            const finalize = (value) => {
                if (!settled) {
                    settled = true;
                    resolve(value);
                }
            };
            this.dialog.add(
                BreakDurationDialog,
                {
                    employeeName: this.state.employee?.name,
                    defaultMinutes: 0,
                    maxMinutes: typeof maxMinutes === "number" ? maxMinutes : undefined,
                    onConfirm: (minutes) => finalize(minutes),
                    onCancel: () => finalize(null),
                },
                {
                    onClose: () => finalize(null),
                }
            );
        });
    }
}

export const systrayAttendance = {
    Component: ActivityMenu,
};

registry
    .category("systray")
    .add("hr_attendance.attendance_menu", systrayAttendance, { sequence: 70 });
