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
            this.state.hasDemoData = await this.orm.call("hr.attendance", "has_demo_data", []);
        });
    }

    loadAttendanceScenario() {
        this.actionService.doAction("hr_attendance.action_load_demo_data");
    }

    LoadTryKiosk() {
        this.actionService.doAction("hr_attendance.action_try_kiosk");
    }
};
