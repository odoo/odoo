/** @odoo-module native */
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/ui/dialog/confirmation_dialog";

import { Component, onWillStart, useState } from "@odoo/owl";

export class AttendanceActionHelper extends Component {
    static template = "hr_attendance.AttendanceActionHelper";
    static props = ["noContentHelp"];
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.state = useState({
            hasDemoData: false,
        });
        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr.group_hr_user");
            this.hasAttendanceRight = await user.hasGroup(
                "hr_attendance.group_hr_attendance_user",
            );
            if (this.hasAttendanceRight && this.isHrUser) {
                this.state.hasDemoData = await this.orm.call(
                    "hr.attendance",
                    "has_demo_data",
                    [],
                );
            }
        });
    }

    loadAttendanceScenario() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t(
                "This creates sample employees, working schedules and attendances across several apps. Are you sure you want to proceed?",
            ),
            confirmLabel: _t("Load Sample Data"),
            confirm: () =>
                this.actionService.doAction("hr_attendance.action_load_demo_data"),
            cancel: () => {},
        });
    }

    LoadTryKiosk() {
        this.actionService.doAction("hr_attendance.action_try_kiosk");
    }
}
