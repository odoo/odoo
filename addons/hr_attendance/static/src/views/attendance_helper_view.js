import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart, proxy } from "@odoo/owl";

export class AttendanceActionHelper extends Component {
    static template = "hr_attendance.AttendanceActionHelper";
    static props = ["noContentHelp"];
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = proxy({
            hasDemoData: false,
        });
        onWillStart(async () => {
            [this.isHrUser, this.hasAttendanceRight] = await Promise.all([
                user.hasGroup("hr.group_hr_user"),
                user.hasGroup("hr_attendance.group_hr_attendance_user"),
            ]);
            if (this.hasAttendanceRight && this.isHrUser) {
                this.state.hasDemoData = await this.orm.call("hr.attendance", "has_demo_data", []);
            }
        });
    }

    loadAttendanceScenario() {
        this.actionService.doAction("hr_attendance.action_load_demo_data");
    }

    LoadTryKiosk() {
        this.actionService.doAction("hr_attendance.action_try_kiosk");
    }
}
