import { Component, onWillStart, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { rpc, ConnectionLostError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isIosApp } from "@web/core/browser/feature_detection";
import { BreakDurationDialog } from "@hr_attendance/components/break_duration_dialog/break_duration_dialog";

export class ActivityMenu extends Component {
    static components = { Dropdown, DropdownItem };
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.lazySession = useService("lazy_session");
        this.notification = useService("notification");
        this.employee = false;
        this.state = useState({
            checkedIn: false,
            isDisplayed: false,
        });

        this.date_formatter = registry.category("formatters").get("float_time");
        this.dropdown = useDropdownState();

        onWillStart(() => {
            this.lazySession.getValue("attendance_user_data", (employee) => {
                if (employee) {
                    this.employee = employee;
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
        this.state.isDisplayed = this.employee.display_systray;
        this.state.checkedIn = this.employee.attendance_state === "checked_in";

        this.hoursToday = this.date_formatter(this.employee.hours_today);

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
                duration: this.date_formatter(duration),
            };
        });
        this.hasCheckedInToday = this.attendancesToday.length > 0;
    }

    splitTime(timeStr) {
        const [h, m] = timeStr.split(":");
        return { h, m };
    }

    async checking(latitude = false, longitude = false, breakDurationHours = null) {
        try {
            this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                latitude,
                longitude,
                break_duration: breakDurationHours,
            });
            this._searchReadEmployeeFill();
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

    async signInOut() {
        this.dropdown.close();
        if (this._attendanceInProgress) {
            return;
        }
        this._attendanceInProgress = true;

        try {
            await this.searchReadEmployee();
            if (!this.employee || !this.employee.id) {
                this._attendanceInProgress = false;
                return;
            }
            let breakDurationHours = null;
            if (this.employee.break_management_enabled && this.employee.attendance_state === "checked_in") {
                const minutes = await this.requestBreakDuration();
                if (minutes === null) {
                    this._attendanceInProgress = false;
                    return;
                }
                breakDurationHours = (Number(minutes) || 0) / 60;
            }
            const trackingEnabled = this.employee && this.employee.device_tracking_enabled;
            if (trackingEnabled && !isIosApp() && navigator.geolocation && navigator.onLine) {
                // iOS app lacks permissions to call `getCurrentPosition`
                navigator.geolocation.getCurrentPosition(
                    async ({ coords: { latitude, longitude } }) => {
                        await this.checking(latitude, longitude, breakDurationHours);
                    },
                    async () => {
                        await this.checking(false, false, breakDurationHours);
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                    }
                );
            } else {
                await this.checking(false, false, breakDurationHours);
            }
        } catch (error) {
            this._attendanceInProgress = false;
            throw error;
        }
    }

    async requestBreakDuration() {
        return new Promise((resolve) => {
            let settled = false;
            const finalize = (value) => {
                if (!settled) {
                    settled = true;
                    resolve(value);
                }
            };
            this.dialog.add(BreakDurationDialog, {
                employeeName: this.employee?.name,
                defaultMinutes: 0,
                onConfirm: (minutes) => finalize(minutes),
                onCancel: () => finalize(null),
            });
        });
    }
}

export const systrayAttendance = {
    Component: ActivityMenu,
};

registry
    .category("systray")
    .add("hr_attendance.attendance_menu", systrayAttendance, { sequence: 101 });
