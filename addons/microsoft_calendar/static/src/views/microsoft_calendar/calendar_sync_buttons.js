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
        this.state.microsoftSyncIsDone = false;
        this.state.microsoftSyncIsPaused = this.microsoftSyncStatus === "sync_paused";
    },

    async onMicrosoftSyncCalendar() {
        await this.orm.call(
            "res.users",
            "restart_microsoft_synchronization",
            [[user.userId]],
        );
        const syncResult = await this.syncMicrosoftCalendar();
        if (syncResult.status === "need_auth") {
            window.location.assign(syncResult.url);
        } else if (syncResult.status === "need_config_from_admin") {
            if (this.isSystemUser) {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Configuration"),
                    body: _t("The Outlook Synchronization needs to be configured before you can use it, do you want to do it now?"),
                    confirm: this.actionService.doAction.bind(this.actionService, syncResult.action),
                    confirmLabel: _t("Configure"),
                    cancel: () => {},
                    cancelLabel: _t("Discard"),
                });
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Configuration"),
                    body: _t("An administrator needs to configure Outlook Synchronization before you can use it!"),
                });
            }
        } else {
            await this.load();
            this.render(true);
        }
    },

    async onStopMicrosoftSynchronization() {
        await this.orm.call(
            "res.users",
            "stop_microsoft_synchronization",
            [[user.userId]],
        );
        await this.load();
        this.render(true);
    },

    async onUnpauseMicrosoftSynchronization() {
        await this.orm.call(
            "res.users",
            "unpause_microsoft_synchronization",
            [[user.userId]],
        );
        await this.onStopMicrosoftSynchronization();
        this.render(true);
    },

    async syncMicrosoftCalendar(silent = false) {
        this.microsoftPendingSync = true;
        const result = await rpc(
            "/microsoft_calendar/sync_data",
            {
                model: "calendar.event",
                fromurl: window.location.href
            },
            {
                silent,
            },
        );
        if (["need_config_from_admin", "need_auth", "sync_stopped", "sync_paused"].includes(result.status)) {
            this.state.microsoftIsSync = false;
        } else if (result.status === "no_new_event_from_microsoft" || result.status === "need_refresh") {
            this.state.microsoftIsSync = true;
        }
        this.state.microsoftIsPaused = result.status == "sync_paused";
        this.microsoftPendingSync = false;
        return result;
    },
});
