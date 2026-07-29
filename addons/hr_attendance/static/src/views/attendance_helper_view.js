import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart, proxy } from "@odoo/owl";

export class AttendanceActionHelper extends Component {
    static template = "hr_attendance.AttendanceActionHelper";
    static props = ["noContentHelp"];
    setup() {
        this.actionService = useService("action");
        this.uiService = useService("ui");
        this.dialogService = useService("dialog");
        this.state = proxy({
            hasDemoData: true,
        });
        const lazySession = useService("lazy_session");
        onWillStart(async () => {
            [this.isHrUser, this.hasAttendanceRight] = await Promise.all([
                user.hasGroup("hr.group_hr_user"),
                user.hasGroup("hr_attendance.group_hr_attendance_user"),
            ]);
            if (this.hasAttendanceRight && this.isHrUser) {
                lazySession.getValue("is_demo", (v) => (this.state.hasDemoData = !!v));
            }
        });
    }

    loadAttendanceScenario() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("This action will generate several fake records across multiple apps. Are you sure you want to proceed?"),
            confirmLabel: _t("Load Sample Data"),
            cancelLabel: _t("Cancel"),
            confirm: () => this.actionService.doAction("hr_attendance.action_load_demo_data"),
            cancel: () => { },
        });
    }

    LoadTryKiosk() {
        this.actionService.doAction("hr_attendance.action_try_kiosk");
    }
}
