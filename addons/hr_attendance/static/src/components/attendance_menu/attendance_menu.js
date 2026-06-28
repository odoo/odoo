import { Component, onWillStart, proxy } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc, ConnectionLostError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { formatFloatTime } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { isIosApp } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { AttendanceVideoStream } from "@hr_attendance/components/attendance_video_stream/attendance_video_stream";

export class ActivityMenu extends Component {
    static components = { Dropdown, DropdownItem, AttendanceVideoStream };
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.ui = useService("ui");
        this.lazySession = useService("lazy_session");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        this.employee = false;
        this.state = proxy({
            checkedIn: false,
            isDisplayed: false,
            captureCheckInImage: false,
            streamAvailable: null,
        });
        this.cameraCapture = null;
        this.dropdown = useDropdownState();
        onWillStart(() => {
            this.lazySession.getValue("attendance_user_data", (employee) => {
                if (employee) {
                    this.employee = employee;
                    this.attendanceCheckInPermission = employee.has_attendance_check_in_ability;
                    this._searchReadEmployeeFill();
                }
            });
        });
    }

    async searchReadEmployee() {
        this.employee = await rpc("/hr_attendance/attendance_user_data");
        this._searchReadEmployeeFill();
    }

    _searchReadEmployeeFill() {
        if (!this.employee?.id) {
            this.state.isDisplayed = false;
            return;
        }

        this.employeeName = this.employee.name;
        this.state.isDisplayed = this.attendanceCheckInPermission;
        this.state.checkedIn = this.employee.attendance_state === "checked_in";
        this.state.captureCheckInImage =
            this.employee.capture_check_in_image && !this.state.checkedIn;

        this.hoursToday = formatFloatTime(this.employee.hours_today, { numeric: true });

        this.attendancesToday = (this.employee.today_attendance_ids || []).map((att) => {
            const checkIn = deserializeDateTime(att.check_in).toLocaleString({
                hour: "2-digit",
                minute: "2-digit",
            });
            const checkOut = att.check_out
                ? deserializeDateTime(att.check_out).toLocaleString({
                      hour: "2-digit",
                      minute: "2-digit",
                  })
                : null;
            const duration = att.check_out
                ? att.worked_hours
                : this.employee.last_attendance_worked_hours;
            return {
                id: att.id,
                start: checkIn,
                end: checkOut,
                duration: formatFloatTime(duration, { numeric: true }),
            };
        });
        this.hasCheckedInToday = this.attendancesToday.length > 0;
    }

    splitTime(timeStr) {
        const [h, m] = timeStr.split(":");
        return { h, m };
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
        this.searchReadEmployee();
    }

    async checking({ latitude = false, longitude = false, checkInImage = null } = {}) {
        try {
            this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                latitude,
                longitude,
                check_in_image: checkInImage,
            });
            this._searchReadEmployeeFill();
            if (this.employee?.notification?.message) {
                this.notification.add(this.employee.notification.message, {
                    type: this.employee.notification.type,
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
            cancel: () => (this._attendanceInProgress = false),
        });
    }

    get closeSystrayOnCheckIn() {
        return true;
    }

    async signInOut() {
        const checkInImage = this.cameraCapture?.();
        if (this.closeSystrayOnCheckIn) {
            this.dropdown.close();
        }
        if (this._attendanceInProgress) {
            return;
        }
        this._attendanceInProgress = true;

        const trackingEnabled = this.employee && this.employee.device_tracking_enabled;
        if (trackingEnabled && !isIosApp() && navigator.geolocation && navigator.onLine) {
            // iOS app lacks permissions to call `getCurrentPosition`
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
