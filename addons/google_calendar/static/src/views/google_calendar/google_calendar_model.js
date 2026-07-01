import { proxy } from "@odoo/owl";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel.prototype, {
    setup(params) {
        super.setup(...arguments);
        this.isAlive = params.isAlive;
        this.googleSyncTimedOut = false;
        this.state = proxy({
            googlePendingSync: false,
            googleIsSync: true,
            googleIsPaused: false,
            googleSyncError: false,
        });
    },

    /**
     * @override
     */
    async updateData() {
        const reason = this.meta.loadReason;
        this.meta.loadReason = undefined;
        this.googleSyncTimedOut = false;
        if (reason === "filters_update" || this.state.googlePendingSync) {
            return super.updateData(...arguments);
        }
        try {
            this.googleSyncTimedOut = await Promise.race([
                new Promise(resolve => setTimeout(resolve, 1000)).then(() => true),
                this.syncGoogleCalendar(true).then(() => false),
            ]);
        } catch (error) {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize Google events now.", error);
            this.state.googlePendingSync = false;
        }
        if (this.isAlive()) {
            return super.updateData(...arguments);
        }
        return new Promise(() => {});
    },

    async syncGoogleCalendar(silent = false) {
        this.state.googlePendingSync = true;
        const params = new URLSearchParams(window.location.search);
        if (params.get("auth_success")) {
            await this.orm.call(
                "res.users",
                "restart_google_synchronization",
            );
        }

        const result = await rpc(
            "/google_calendar/sync_data",
            {
                model: this.resModel,
                fromurl: window.location.href
            },
            {
                silent,
            },
        );
        if (["need_config_from_admin", "need_auth", "sync_stopped", "sync_paused", "sync_failed"].includes(result.status)) {
            this.state.googleIsSync = false;
        } else if (result.status === "no_new_event_from_google" || result.status === "need_refresh") {
            this.state.googleIsSync = true;
        }
        this.state.googleSyncError = result.status === "sync_failed";
        this.state.googleIsPaused = result.status === "sync_paused";
        this.state.googlePendingSync = false;
        if (this.googleSyncTimedOut && result.status === "need_refresh") {
            const data = { ...this.data };
            await this.keepLast.add(super.updateData(data));
            this.data = data;
            this.notify();
        }
        return result;
    },

    get googleCredentialsSet() {
        return this.credentialStatus['google_calendar'] ?? false;
    }
});
