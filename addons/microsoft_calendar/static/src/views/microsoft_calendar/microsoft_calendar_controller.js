/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(AttendeeCalendarController.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    async onMicrosoftSyncCalendar() {
        await this.orm.call(
            "res.users",
            "restart_microsoft_synchronization",
            [[this.user.userId]],
        );
        const syncResult = await this.model.syncMicrosoftCalendar();
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
        } else if (syncResult.status === "need_refresh") {
            await this.model.load();
        }
    },

    async onStopMicrosoftSynchronization() {
        this.dialog.add(ConfirmationDialog, {
            body: _t("You are about to stop the synchronization of your calendar with Outlook. Are you sure you want to continue?"),
            confirmLabel: _t("Stop Synchronization"),
            confirm: async () => {
                await this.orm.call(
                    "res.users",
                    "stop_microsoft_synchronization",
                    [[this.user.userId]],
                );
                this.notification.add(
                    _t("The synchronization with Outlook calendar was successfully stopped."),
                    {
                        title: _t("Success"),
                        type: "success",
                    },
                );
                await this.model.load();
            },
        });
    },

    onMicrosoftSyncUnpause() {
        if (this.isSystemUser) {
            this.env.services.action.doAction("calendar.calendar_settings_action");
        } else {
            this.dialog.add(AlertDialog, {
                title: _t("Configuration"),
                body: _t("Your administrator paused the synchronization with Outlook Calendar."),
            });
        }
    }
});
