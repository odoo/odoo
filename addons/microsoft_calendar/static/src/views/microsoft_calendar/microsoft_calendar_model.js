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
        this.microsoftSyncTimedOut = false;
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
        this.microsoftSyncTimedOut = false;
        if (this.state.microsoftPendingSync) {
            return super.updateData(...arguments);
        }
        try {
            this.microsoftSyncTimedOut = await Promise.race([
                new Promise(resolve => setTimeout(resolve, 1000)).then(() => true),
                this.syncMicrosoftCalendar(true).then(() => false),
            ]);
        } catch (error) {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize microsoft events now.", error);
            this.state.microsoftPendingSync = false;
        }
        if (this.isAlive()) {
            return super.updateData(...arguments);
        }
        return new Promise(() => {});
    },

    async syncMicrosoftCalendar(silent = false) {
        this.state.microsoftPendingSync = true;
        const params = new URLSearchParams(window.location.search);
        if (params.get("auth_success")) {
            await this.orm.call("res.users", "restart_microsoft_synchronization");
        }

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
        if (this.microsoftSyncTimedOut && result.status === "need_refresh") {
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
