import { Component, onWillStart, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isIosApp } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
const { DateTime } = luxon;

export class ActivityMenu extends Component {
    static components = {Dropdown, DropdownItem};
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.ui = useService("ui");
        this.lazySession = useService("lazy_session");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.employee = false;
        this.state = useState({
            checkedIn: false,
            isDisplayed: false
        });
        this.date_formatter = registry.category("formatters").get("float_time")
        this.dropdown = useDropdownState();
        this.pollingInterval = null;

        onWillStart(()=> {
            // access lazy session but do no wait for it, to prevent from delaying the whole webclient
            this.lazySession.getValue("attendance_user_data", (employee) => {
                if (employee) {
                    this.employee = employee;
                    this._searchReadEmployeeFill();
                }
            });
        });

        onMounted(() => {
            // Request browser notification permission
            if ("Notification" in window && Notification.permission === "default") {
                Notification.requestPermission();
            }

            // Start polling every 1 minute (60000 ms)
            this.pollingInterval = setInterval(() => {
                this._pollAttendanceData();
            }, 60000);
        });

        onWillUnmount(() => {
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
            }
        });
    }

    async searchReadEmployee(){
        this.employee = await rpc("/hr_attendance/attendance_user_data");
        this._searchReadEmployeeFill();
    }

    _searchReadEmployeeFill() {
        if (this.employee.id) {
            this.hoursToday = this.date_formatter(
                this.employee.hours_today
            );
            this.hoursPreviouslyToday = this.date_formatter(
                this.employee.hours_previously_today
            );
            this.lastAttendanceWorkedHours = this.date_formatter(
                this.employee.last_attendance_worked_hours
            );
            this.lastCheckIn = deserializeDateTime(this.employee.last_check_in).toLocaleString(DateTime.TIME_SIMPLE);
            this.state.checkedIn = this.employee.attendance_state === "checked_in";
            this.isFirstAttendance = this.employee.hours_previously_today === 0;
            this.state.isDisplayed = this.employee.display_systray

            // Check if employee exceeded 8 hours and show notification
            if (this.employee.exceeded_eight_hours && !this._hasAcknowledgedToday()) {
                this._showEightHourNotification();
            }
        } else {
            this.state.isDisplayed = false
        }
    }

    _hasAcknowledgedToday() {
        // Check localStorage to see if user already acknowledged notification today
        const today = new Date().toDateString();
        const acknowledgedDate = localStorage.getItem('attendance_8h_acknowledged');
        return acknowledgedDate === today;
    }

    _markAsAcknowledged() {
        // Store today's date in localStorage
        const today = new Date().toDateString();
        localStorage.setItem('attendance_8h_acknowledged', today);
    }

    async _pollAttendanceData() {
        // Only poll if employee is checked in
        if (this.state.checkedIn && this.employee && this.employee.id) {
            try {
                this.employee = await rpc("/hr_attendance/attendance_user_data");
                this._searchReadEmployeeFill();
            } catch (error) {
                console.error("[AttendanceMenu] Polling error:", error);
            }
        }
    }

    _showEightHourNotification() {
        console.log("[AttendanceMenu] 8-hour notification triggered!");
        console.log("[AttendanceMenu] Dialog service available:", !!this.dialog);

        // Use setTimeout to ensure component is fully mounted
        setTimeout(() => {
            try {
                this.dialog.add(AlertDialog, {
                    title: _t("⏰ 8 Hours Reached"),
                    body: _t("You have worked 8 hours today.\nConsider taking a break or checking out."),
                    confirmLabel: _t("OK"),
                    confirmClass: "btn-primary",
                    confirm: () => {
                        // Mark as acknowledged when user clicks OK
                        this._markAsAcknowledged();
                        console.log("[AttendanceMenu] User acknowledged 8-hour notification");
                    },
                });
                console.log("[AttendanceMenu] Dialog added successfully");
            } catch (error) {
                console.error("[AttendanceMenu] Failed to show dialog:", error);
            }
        }, 100);

        // Show browser notification if permission granted
        if ("Notification" in window && Notification.permission === "granted") {
            new Notification(_t("8 Hours Reached"), {
                body: _t("You have worked 8 hours today. Consider taking a break or checking out."),
                icon: "/web/static/img/favicon.ico",
                tag: "attendance-8hours",
            });
        }
    }

    async signInOut() {
        this.dropdown.close();

        const trackingEnabled = this.employee && this.employee.device_tracking_enabled;
        if (trackingEnabled && !isIosApp() && navigator.geolocation) {
            // iOS app lacks permissions to call `getCurrentPosition`
            navigator.geolocation.getCurrentPosition(
                async ({coords: {latitude, longitude}}) => {
                    this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                        latitude,
                        longitude
                    })
                    this._searchReadEmployeeFill();
                },
                async err => {
                    this.employee = await rpc("/hr_attendance/systray_check_in_out")
                    this._searchReadEmployeeFill();
                },
                {
                    enableHighAccuracy: true,
                }
            )
        } else {
            this.employee = await rpc("/hr_attendance/systray_check_in_out")
            this._searchReadEmployeeFill();
        }
    }
}

export const systrayAttendance = {
    Component: ActivityMenu,
};

registry
    .category("systray")
    .add("hr_attendance.attendance_menu", systrayAttendance, { sequence: 101 });
