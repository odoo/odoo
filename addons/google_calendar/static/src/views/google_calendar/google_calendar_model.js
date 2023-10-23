/** @odoo-module **/

import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel, {
    services: [...AttendeeCalendarModel.services, "rpc"],
});

patch(AttendeeCalendarModel.prototype, {
    setup(params, { rpc }) {
        super.setup(...arguments);
        this.rpc = rpc;
        this.googleIsSync = true;
        this.googlePendingSync = false;
        this.googleIsPaused = false;
    },

    /**
     * @override
     */
    async updateData() {
        if (this.googlePendingSync) {
            return super.updateData(...arguments);
        }
        try {
            await Promise.race([
                new Promise(resolve => setTimeout(resolve, 1000)),
                this.syncGoogleCalendar(true)
            ]);
        } catch (error) {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize Google events now.", error);
            this.googlePendingSync = false;
        }
        return super.updateData(...arguments);
    },

    async syncGoogleCalendar(silent = false) {
        this.googlePendingSync = true;
        const result = await this.rpc(
            "/google_calendar/sync_data",
            {
                model: this.resModel,
                fromurl: window.location.href
            },
            {
                silent,
            },
        );
        if (["need_config_from_admin", "need_auth", "sync_stopped", "sync_paused"].includes(result.status)) {
            this.googleIsSync = false;
        } else if (result.status === "no_new_event_from_google" || result.status === "need_refresh") {
            this.googleIsSync = true;
        }
        this.googleIsPaused = result.status == "sync_paused";
        this.googlePendingSync = false;
        return result;
    },

    get googleCredentialsSet() {
        return this.credentialStatus['google_calendar'] ?? false;
    }
});
