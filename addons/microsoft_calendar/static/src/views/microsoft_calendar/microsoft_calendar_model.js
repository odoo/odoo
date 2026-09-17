import { proxy } from "@odoo/owl";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel, {
    services: [...AttendeeCalendarModel.services],
});

patch(AttendeeCalendarModel.prototype, {
    setup(params) {
        super.setup(...arguments);
        this.isAlive = params.isAlive;
        this.state = proxy({
            microsoftSyncError: false,
            microsoftPendingSync: false,
            microsoftIsSync: true,
            microsoftIsPaused: false,
        })
    },

    /**
     * @override
     */
    async updateData() {
        if (this.state.microsoftPendingSync) {
            return super.updateData(...arguments);
        }
        this.syncMicrosoftCalendar(true).catch((error) => {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize microsoft events now.", error);
            this.state.microsoftPendingSync = false;
        })
        if (this.isAlive()) {
            return super.updateData(...arguments);
        }
        return new Promise(() => {});
    },

    async syncMicrosoftCalendar(silent = false) {
        this.state.microsoftPendingSync = true;
        const result = await rpc(
            "/microsoft_calendar/sync_data",
            {
                model: this.resModel,
                fromurl: window.location.href
            },
            {
                silent,
            },
        );
        if (["need_config_from_admin", "need_auth", "sync_stopped", "sync_paused", "sync_failed"].includes(result.status)) {
            this.state.microsoftIsSync = false;
        } else if (result.status === "no_new_event_from_microsoft" || result.status === "need_refresh") {
            this.state.microsoftIsSync = true;
        }
        this.state.microsoftSyncError = result.status === "sync_failed";
        this.state.microsoftIsPaused = result.status === "sync_paused";
        this.state.microsoftPendingSync = false;
        if (result.status === "need_refresh") {
            const data = { ...this.data };
            await this.keepLast.add(super.updateData(data));
            this.data = data;
            this.notify();
        }
        return result;
    },

    get microsoftCredentialsSet() {
        return this.credentialStatus['microsoft_calendar'] ?? false;
    }
});
