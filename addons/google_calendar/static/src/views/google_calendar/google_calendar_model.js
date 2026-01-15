import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(AttendeeCalendarModel.prototype, {
    setup(params) {
        super.setup(...arguments);
        this.isAlive = params.isAlive;
        this.googleSyncTimedOut = false;
        this.state = useState({
            googlePendingSync: false,
            googleIsSync: true,
            googleIsPaused: false,
        });
    },

    /**
     * @override
     */
    async updateData() {
        this.googleSyncTimedOut = false;
        if (this.state.googlePendingSync) {
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

    async syncGoogleCalendar(silent = false, force_auth = false) {
        this.state.googlePendingSync = true;
        const result = await rpc(
            "/google_calendar/sync_data",
            {
                model: this.resModel,
                force_auth: force_auth,
                fromurl: window.location.href
            },
            {
                silent,
            },
        );
        if (["need_config_from_admin", "need_auth", "sync_stopped", "sync_paused"].includes(result.status)) {
            this.state.googleIsSync = false;
        } else if (result.status === "no_new_event_from_google" || result.status === "need_refresh") {
            this.state.googleIsSync = true;
        }
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
