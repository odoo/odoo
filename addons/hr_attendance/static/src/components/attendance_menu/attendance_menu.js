/** @odoo-module native */
import { luxon } from "@web/core/l10n/luxon";
import { Component, onWillStart, useState } from "@odoo/owl";
import { Dropdown, DropdownItem, useDropdownState } from "@web/components/dropdown";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc, ConnectionLostError } from "@web/core/network";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isIosApp } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/translation";
import { ConfirmationDialog } from "@web/ui/dialog/confirmation_dialog";
const { DateTime } = luxon;

export class ActivityMenu extends Component {
    static components = { Dropdown, DropdownItem };
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.ui = useService("ui");
        this.lazySession = useService("lazy_session");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
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
        if (this.employee.id) {
            this.hoursToday = this.date_formatter(this.employee.hours_today);
            this.hoursPreviouslyToday = this.date_formatter(
                this.employee.hours_previously_today,
            );
            this.lastAttendanceWorkedHours = this.date_formatter(
                this.employee.last_attendance_worked_hours,
            );
            this.lastCheckIn = deserializeDateTime(
                this.employee.last_check_in,
            ).toLocaleString(DateTime.TIME_SIMPLE);
            this.state.checkedIn = this.employee.attendance_state === "checked_in";
            this.isFirstAttendance = this.employee.hours_previously_today === 0;
            this.state.isDisplayed = this.employee.display_systray;
        } else {
            this.state.isDisplayed = false;
        }
    }

    async checking(latitude = false, longitude = false) {
        try {
            this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                latitude,
                longitude,
            });
            this._searchReadEmployeeFill();
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.notification.add(
                    _t("Connection lost. Check in/out could not be recorded."),
                    {
                        title: _t("Attendance Error"),
                        type: "danger",
                        sticky: false,
                    },
                );
            } else {
                throw error;
            }
        } finally {
            this._attendanceInProgress = false;
        }
    }

    /**
     * Location tracking is on but the browser gave us no coordinates. Only
     * record the attendance if the employee accepts that it goes in without
     * one.
     */
    confirmChecking() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t(
                "Unable to get a valid location. Do you want to proceed with your check-in/out anyway?",
            ),
            confirmLabel: _t("Proceed Anyway"),
            confirm: async () => await this.checking(),
            cancel: () => {
                this._attendanceInProgress = false;
            },
        });
    }

    async signInOut() {
        this.dropdown.close();
        if (this._attendanceInProgress) {
            return;
        }
        this._attendanceInProgress = true;

        const trackingEnabled = this.employee && this.employee.device_tracking_enabled;
        if (
            trackingEnabled &&
            !isIosApp() &&
            navigator.geolocation &&
            navigator.onLine
        ) {
            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude, longitude } }) => {
                    await this.checking(latitude, longitude);
                },
                () => {
                    this.confirmChecking();
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                },
            );
        } else if (trackingEnabled) {
            // iOS app, offline, or no geolocation API at all: ask as well
            // instead of recording an attendance with no location.
            this.confirmChecking();
        } else {
            await this.checking();
        }
    }
}

export const systrayAttendance = {
    Component: ActivityMenu,
};

registry
    .category("systray")
    .add("hr_attendance.attendance_menu", systrayAttendance, { sequence: 101 });
