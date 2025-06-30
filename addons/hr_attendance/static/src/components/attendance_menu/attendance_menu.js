/* @odoo-module */


import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { isIosApp } from "@web/core/browser/feature_detection";
const { DateTime } = luxon;

export class ActivityMenu extends Component {
    static components = {Dropdown, DropdownItem};
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.rpc = useService("rpc");
        this.ui = useState(useService("ui"));
        this.userService = useService("user");
        this.employee = false;
        this.state = useState({
            checkedIn: false,
            isDisplayed: false
        });
        this.signInOut = debounce(this.signInOut, 1000, true);
        this.date_formatter = registry.category("formatters").get("float_time")
        // load data but do not wait for it to render to prevent from delaying
        // the whole webclient
        this.searchReadEmployee();
    }

    async searchReadEmployee(){
        const result = await this.rpc("/hr_attendance/attendance_user_data");
        this.employee = result;
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
        } else {
            this.state.isDisplayed = false
        }
    }

    async signInOut() {
        // to close the dropdown
        document.body.click()
        // iOS app lacks permissions to call `getCurrentPosition`
        if (!isIosApp()) {
            navigator.geolocation.getCurrentPosition(
                async ({coords: {latitude, longitude}}) => {
                    await this.rpc("/hr_attendance/systray_check_in_out", {
                        latitude,
                        longitude
                    })
                    await this.searchReadEmployee()
                },
                async err => {
                    await this.rpc("/hr_attendance/systray_check_in_out")
                    await this.searchReadEmployee()
                },
                {
                    enableHighAccuracy: true,
                }
            )
        } else {
            await this.rpc("/hr_attendance/systray_check_in_out")
            await this.searchReadEmployee()
        }
    }
}

export const systrayAttendance = {
    Component: ActivityMenu,
};

registry
    .category("systray")
    .add("hr_attendance.attendance_menu", systrayAttendance, { sequence: 101 });
