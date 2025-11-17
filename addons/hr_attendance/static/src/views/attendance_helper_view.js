import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart, useState } from "@odoo/owl";

export class AttendanceActionHelper extends Component {
    static template = "hr_attendance.AttendanceActionHelper";
    static props = ["noContentHelp"];
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            hasDemoData: false,
        });
        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr.group_hr_user");
            this.hasAttendanceRight = await user.hasGroup("hr_attendance.group_hr_attendance_user");
            if (this.hasAttendanceRight && this.isHrUser){
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
};
