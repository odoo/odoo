import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { ActionHelper } from "@web/views/action_helper";

import { Component, onWillStart, proxy, t, usePlugin, useProps } from "@odoo/owl";
import { LazySessionPlugin } from "@web/webclient/lazy_session_plugin";

export class AttendanceActionHelper extends Component {
    static template = "hr_attendance.AttendanceActionHelper";
    static components = { ActionHelper };

    props = useProps({
        noContentHelp: t.any(),
    });
    setup() {
        this.actionService = useService("action");
        this.uiService = useService("ui");
        this.dialogService = useService("dialog");
        this.state = proxy({
            hasDemoData: true,
        });
        const lazySession = usePlugin(LazySessionPlugin);
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

    /**
     * The onboarding (try the kiosk, load sample data) is for the users who manage attendances,
     * out of My Attendances. The others get the help of the action.
     */
    get showOnboarding() {
        return this.hasAttendanceRight && this.isHrUser && !this.env.searchModel?.context.my_attendances;
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
