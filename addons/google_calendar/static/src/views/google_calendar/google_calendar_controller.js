import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(AttendeeCalendarController.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    async onGoogleSyncCalendar() {
        /* Force auth, to offer the user the choice of an account to synchronize.
        If the authorization is successful, it will set the google_synchronization_stopped
        flag to false. See `oauth2callback` */
        const syncResult = await this.model.syncGoogleCalendar(false, true);
        if (syncResult.status === "need_auth") {
            window.location.assign(syncResult.url);
        } else if (syncResult.status === "need_config_from_admin") {
            if (this.isSystemUser) {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Configuration"),
                    body: _t("The Google Synchronization needs to be configured before you can use it, do you want to do it now?"),
                    confirm: this.actionService.doAction.bind(this.actionService, syncResult.action),
                    confirmLabel: _t("Configure"),
                    cancel: () => {},
                });
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Configuration"),
                    body: _t("An administrator needs to configure Google Synchronization before you can use it!"),
                });
            }
        }
    },

    async onStopGoogleSynchronization() {
        await this.actionService.doAction("google_calendar.google_calendar_reset_account_action");
    },

    async onUnpauseGoogleSynchronization() {
        await this.orm.call(
            "res.users",
            "unpause_google_synchronization",
            [[user.userId]],
        );
        this.render(true);
    }
});
