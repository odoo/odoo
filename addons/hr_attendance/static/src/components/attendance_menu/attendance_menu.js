import { Component, onWillStart } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isIosApp } from "@web/core/browser/feature_detection";

export class ActivityMenu extends Component {
    static components = { Dropdown, DropdownItem };
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.dropdown = useDropdownState();
        onWillStart(() => this.searchReadEmployee());
    }

    get employee() {
        return this.store.self_employee;
    }

    searchReadEmployee() {
        this.store.fetchStoreData("/hr_attendance/user_data");
    }

    signInOut() {
        this.dropdown.close();
        const checkInOut = (coords) =>
            this.store.fetchStoreData("/hr_attendance/systray_check_in_out", coords, {
                readonly: false,
            });
        if (!isIosApp()) {
            // iOS app lacks permissions to call `getCurrentPosition`
            navigator.geolocation.getCurrentPosition(
                ({ latitude, longitude }) => checkInOut({ latitude, longitude }),
                () => checkInOut(),
                { enableHighAccuracy: true }
            );
        } else {
            checkInOut();
        }
    }
}

export const systrayAttendance = {
    Component: ActivityMenu,
};

registry
    .category("systray")
    .add("hr_attendance.attendance_menu", systrayAttendance, { sequence: 101 });
