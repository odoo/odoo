import { CalendarSyncButtons } from "@calendar/views/widgets/calendar_sync_buttons/calendar_sync_buttons";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(CalendarSyncButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action")
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },


    async initSyncValues() {
        await super.initSyncValues();
        this.state.googleSyncIsDone = true;
        this.state.googleSyncIsPaused = this.googleSyncStatus === "sync_paused";
    },

    async onGoogleSyncCalendar() {
        await this.orm.call(
            "res.users",
            "restart_google_synchronization",
            [[user.userId]],
        );
        const syncResult = await this.syncGoogleCalendar();
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
                    cancelLabel: _t("Discard"),
                });
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Configuration"),
                    body: _t("An administrator needs to configure Google Synchronization before you can use it!"),
                });
            }
        } else {
            await this.props.record.model.load();  // This will make sure all data is updated (mostly in config params?) NEEDED?
            this.render(true);  // This will restart the component, right? to check (true role?)
        }
    },

    async onStopGoogleSynchronization() {
        await this.orm.call(
            "res.users",
            "stop_google_synchronization",
            [[user.userId]],
        );
        await this.props.record.model.load();
        this.render(true);
    },

    async onUnpauseGoogleSynchronization() {
        await this.orm.call(
            "res.users",
            "unpause_google_synchronization",
            [[user.userId]],
        );
        await this.onStopGoogleSynchronization();
        this.render(true);
    },

    async syncGoogleCalendar(silent = false) {
        this.googlePendingSync = true;
        const result = await rpc(
            "/google_calendar/sync_data",
            {
                model: "calendar.event",
                fromurl: window.location.href
            },
            {
                silent,
            },
        );
        if (["need_config_from_admin", "need_auth", "sync_stopped", "sync_paused"].includes(result.status)) {
            this.state.googleSyncIsDone = false;
        } else if (result.status === "no_new_event_from_google" || result.status === "need_refresh") {
            this.state.googleSyncIsDone = true;
        }
        this.state.googleSyncIsPaused = result.status == "sync_paused";
        this.googlePendingSync = false;
        return result;
    },
});
