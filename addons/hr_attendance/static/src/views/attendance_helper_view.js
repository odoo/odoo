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
            this.employeeNumber = await this.orm.searchCount(
                "hr.employee", []);
            const demoEmployeesCount = await this.orm.search(
                "hr.employee", [["category_ids.name", "=", "Demo"]]);
            const demoDataIsActive = await this.orm.searchCount(
                "ir.module.module", [["demo", "=", "True"]]);
            // Mitchell Admin record is to ensure that normal demo data are not installed
            // while others records are to ensure that onboarding demo data are not installed
            this.state.hasDemoData = demoEmployeesCount.length > 0 || demoDataIsActive;
        });
    }

    loadAttendanceScenario() {
        this.actionService.doAction("hr_attendance.action_load_demo_data");
    }

    LoadTryKiosk() {
        this.actionService.doAction("hr_attendance.action_try_kiosk");
    }
};
