import { Component, onWillStart, proxy } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc, ConnectionLostError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { formatFloatTime, formatDateTime } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Record } from "@web/model/record";
import { usePopover } from "@web/core/popover/popover_hook";
import { useSubEnv } from "@web/owl2/utils";
import { AttendanceInlineForm } from "@hr_attendance/components/attendance_inline_form/attendance_inline_form";
import { AttendanceVideoStream } from "@hr_attendance/components/attendance_video_stream/attendance_video_stream";

const { DateTime } = luxon;

export class ActivityMenu extends Component {
    static components = { Dropdown, Record, AttendanceInlineForm, AttendanceVideoStream };
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.ui = useService("ui");
        this.lazySession = useService("lazy_session");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        const { services } = this.env;
        const datetimePicker = services.datetime_picker;
        const attendanceDateTimePicker = Object.create(datetimePicker);
        // Keep datetime picker popovers within the dropdown scope.
        attendanceDateTimePicker.create = (params, options) =>
            datetimePicker.create(
                Object.assign(Object.create(params), {
                    createPopover: (component, popoverOptions) =>
                        usePopover(component, { ...popoverOptions, withScope: true }),
                }),
                options
            );
        useSubEnv({ services: { ...services, datetime_picker: attendanceDateTimePicker } });
        this.state = proxy({
            employee: null,
            attendances: [],
            checkedIn: false,
            isDisplayed: false,
            captureCheckInEnabled: false,
            deviceTrackingEnabled: false,
            breakManagementEnabled: false,
            streamAvailable: null,
            activeAttendance: null,
            attendanceReviewExpanded: true,
            editingAttendanceId: null,
        });

        this.cameraCapture = null;
        this.attendanceRecord = null;
        this.dropdown = useDropdownState();

        onWillStart(() => {
            this.lazySession.getValue("attendance_check_in_ability", (hasAbility) => {
                this.state.isDisplayed = hasAbility;
            });
            this.lazySession.getValue("attendance_state", (attendanceState) => {
                this.state.checkedIn = attendanceState === "checked_in";
            });
            this.lazySession.getValue("attendance_device_tracking", (enabled) => {
                this.state.deviceTrackingEnabled = enabled;
            });
            this.lazySession.getValue("attendance_capture_check_in", (enabled) => {
                this.state.captureCheckInEnabled = enabled;
            });
            this.lazySession.getValue("attendance_break_management", (enabled) => {
                this.state.breakManagementEnabled = enabled;
            });
        });
    }

    async searchReadEmployee() {
        const employee = await rpc("/hr_attendance/attendance_user_data");
        this._searchReadEmployeeFill(employee);
    }

    _searchReadEmployeeFill(employee) {
        this.state.employee = employee || null;
        if (!employee?.id) {
            this.state.isDisplayed = false;
            this.state.attendances = [];
            this.state.activeAttendance = null;
            return;
        }

        this.state.checkedIn = employee.attendance_state === "checked_in";

        const activeAttendanceId = this.state.activeAttendance?.id;
        this.state.attendances = [...(employee.today_attendance_ids || [])].sort(
            (attendanceA, attendanceB) =>
                deserializeDateTime(attendanceA.check_in).ts -
                deserializeDateTime(attendanceB.check_in).ts
        );

        this.state.activeAttendance =
            this.state.attendances.find((attendance) => attendance.id === activeAttendanceId) ||
            this.state.attendances.at(-1) ||
            null;
        const editingAttendance = this._getAttendanceById(this.state.editingAttendanceId);
        if (this.state.editingAttendanceId && (!editingAttendance || !editingAttendance.can_edit)) {
            this._stopInlineEdit();
        }
    }

    get attendanceDetails() {
        const attendance = this.state.activeAttendance;
        if (!attendance) {
            return null;
        }
        let totalDisplayMinutes = 0;
        const sessions = this.state.attendances.map((att) => {
            const checkInDate = deserializeDateTime(att.check_in);
            const checkOutDate = att.check_out ? deserializeDateTime(att.check_out) : null;
            const duration = att.check_out
                ? att.worked_hours
                : this.state.employee.last_attendance_worked_hours;
            const displayMinutes = Math.round(duration * 60);
            totalDisplayMinutes += displayMinutes;
            return {
                id: att.id,
                selected:
                    att.id === this.state.activeAttendance?.id &&
                    this.state.attendanceReviewExpanded !== false,
                checkIn: checkInDate,
                checkOut: checkOutDate,
                durationLabel: formatFloatTime(displayMinutes, {
                    numeric: true,
                    unit: "minutes",
                }),
            };
        });
        const checkIn = deserializeDateTime(attendance.check_in);
        const checkOut = attendance.check_out ? deserializeDateTime(attendance.check_out) : null;
        return {
            id: attendance.id,
            checkIn,
            checkOut,
            inLocation: attendance.in_location || false,
            outLocation: attendance.out_location || false,
            breakDurationLabel: attendance.break_duration
                ? formatFloatTime(attendance.break_duration, { numeric: true })
                : false,
            breakDisplay: formatFloatTime(this.state.employee.break_today, { numeric: true }),
            totalDisplay: formatFloatTime(totalDisplayMinutes, {
                numeric: true,
                unit: "minutes",
            }),
            sessions,
        };
    }

    get todayDateLabel() {
        return DateTime.now().toLocaleString({
            day: "numeric",
            month: "short",
            year: "numeric",
        });
    }

    _getAttendanceById(attendanceId) {
        if (!attendanceId) {
            return null;
        }
        return this.state.attendances.find((attendance) => attendance.id === attendanceId);
    }

    setCameraCapture(capturePicture) {
        this.cameraCapture = capturePicture;
    }

    setStreamAvailable(isAvailable) {
        this.state.streamAvailable = isAvailable;
    }

    get showVideoStream() {
        return (
            this.state.captureCheckInEnabled &&
            !this.state.checkedIn &&
            this.state.streamAvailable !== false
        );
    }

    async beforeDropdownOpen() {
        this.setStreamAvailable(null);
        if (this.state.checkedIn && this.state.showTimesheetsSystray) {
            return;
        }
        await this.refreshAttendanceReview();
    }

    async openAttendanceReview() {
        await this.refreshAttendanceReview();
    }

    async refreshAttendanceReview() {
        await this.searchReadEmployee();
        const latestAttendance = this.state.attendances.at(-1);
        if (latestAttendance) {
            this.state.activeAttendance = latestAttendance;
            this.state.attendanceReviewExpanded = true;
            if (latestAttendance.can_edit) {
                this.startInlineEdit(latestAttendance);
            }
        }
    }

    _formatAttendanceTime(dateTime) {
        return formatDateTime(dateTime, { showDate: false });
    }

    async selectAttendance(attendanceId) {
        if (this.attendanceRecord?.dirty && !(await this.saveAttendanceRecord())) {
            return;
        }
        const attendance = this._getAttendanceById(attendanceId);
        if (!attendance) {
            return;
        }
        if (attendance.id === this.state.activeAttendance?.id && this.state.attendanceReviewExpanded) {
            this._stopInlineEdit();
            this.state.attendanceReviewExpanded = false;
            return;
        }
        if (attendance.can_edit) {
            this.startInlineEdit(attendance);
        } else {
            this._stopInlineEdit();
            this.state.activeAttendance = attendance;
            this.state.attendanceReviewExpanded = true;
        }
    }

    startInlineEdit(attendance = this.state.activeAttendance) {
        if (!attendance?.can_edit) {
            return;
        }
        this.attendanceRecord = null;
        this.state.activeAttendance = attendance;
        this.state.attendanceReviewExpanded = true;
        this.state.editingAttendanceId = attendance.id;
    }

    _stopInlineEdit() {
        this.state.editingAttendanceId = null;
        this.attendanceRecord = null;
    }

    get attendanceRecordProps() {
        return {
            resModel: "hr.attendance",
            fieldNames: [
                "id",
                "check_in",
                "check_out",
                "break_duration",
                "can_edit",
                "in_location",
                "out_location",
            ],
            resId: this.state.editingAttendanceId,
            mode: "edit",
            values: this.attendanceRecord
                ? undefined
                : this._getAttendanceById(this.state.editingAttendanceId),
            hooks: {
                onRootLoaded: (record) => {
                    this.attendanceRecord = record;
                },
            },
        };
    }

    async saveAttendanceRecord(record = this.attendanceRecord) {
        if (!record) {
            return true;
        }
        if (!(await record.checkValidity({ displayNotification: true }))) {
            return false;
        }
        try {
            if (!(await record.save())) {
                return false;
            }
        } catch (error) {
            this._notifyAttendanceError(error);
            return false;
        }
        try {
            await this.searchReadEmployee();
        } catch {
            this.notification.add(_t("Attendance saved, but the display could not be refreshed."), {
                title: _t("Attendance Error"),
                type: "warning",
            });
        }
        return true;
    }

    async discardAttendanceRecord(record = this.attendanceRecord) {
        if (record) {
            await record.discard();
        }
    }

    onFormKeydown(ev) {
        if (ev.key === "Tab") {
            ev.stopPropagation();
        }
    }

    _notifyAttendanceError(error) {
        this.notification.add(
            error?.data?.message || error?.message || _t("Could not update this attendance."),
            {
                title: _t("Attendance Error"),
                type: "danger",
            }
        );
    }

    async checking({ latitude = false, longitude = false, checkInImage = null } = {}) {
        try {
            const employee = await rpc("/hr_attendance/systray_check_in_out", {
                latitude,
                longitude,
                check_in_image: checkInImage,
            });
            this._searchReadEmployeeFill(employee);
            this._stopInlineEdit();
            const latestAttendance = this.state.attendances.at(-1);
            if (this.dropdown.isOpen && latestAttendance?.can_edit) {
                this.startInlineEdit(latestAttendance);
            }
            if (employee?.notification?.message) {
                this.notification.add(employee.notification.message, {
                    type: employee.notification.type,
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

    confirmChecking(checkInImage = null) {
        this.dialogService.add(ConfirmationDialog, {
            body: _t(
                "Unable to get a valid location. Do you want to proceed with your check-in/out anyway?"
            ),
            confirmLabel: _t("Proceed Anyway"),
            confirm: async () => await this.checking({ checkInImage }),
            cancel: () => { this._attendanceInProgress = false; },
        });
    }

    get closeSystrayOnCheckIn() {
        return true;
    }

    async signInOut() {
        if (this._attendanceInProgress) {
            return;
        }
        this._attendanceInProgress = true;
        const attendanceWasCheckedIn = this.state.checkedIn;
        if (this.attendanceRecord?.dirty) {
            if (!(await this.saveAttendanceRecord())) {
                this._attendanceInProgress = false;
                return;
            }
            if (attendanceWasCheckedIn && !this.state.checkedIn) {
                this._stopInlineEdit();
                this.dropdown.close();
                this._attendanceInProgress = false;
                return;
            }
        }
        const checkInImage = this.cameraCapture?.();
        if (this.closeSystrayOnCheckIn) {
            this.dropdown.close();
        }

        const trackingEnabled = this.state.deviceTrackingEnabled;
        if (trackingEnabled && navigator.geolocation && navigator.onLine) {
            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude, longitude } }) => {
                    await this.checking({ latitude, longitude, checkInImage });
                },
                () => {
                    this.confirmChecking(checkInImage);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                }
            );
        } else if (trackingEnabled) {
            this.confirmChecking(checkInImage);
        } else {
            await this.checking({ checkInImage });
        }
    }
}

export const systrayAttendance = {
    Component: ActivityMenu,
};

registry
    .category("systray")
    .add("hr_attendance.attendance_menu", systrayAttendance, { sequence: 70 });
