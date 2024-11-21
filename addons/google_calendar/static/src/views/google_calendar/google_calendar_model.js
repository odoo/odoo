/** @odoo-module **/

import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(AttendeeCalendarModel.prototype, {
    setup(params) {
        super.setup(...arguments);
        this.isAlive = params.isAlive;
        this.googlePendingSync = false;
        this.state = useState({
            googleIsSync: true,
            googleIsPaused: false,
        });
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
        if (this.isAlive()) {
            return super.updateData(...arguments);
        }
        return new Promise(() => {});
    },

    async syncGoogleCalendar(silent = false) {
        this.googlePendingSync = true;
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
        if (["need_config_from_admin", "need_auth", "sync_stopped", "sync_paused"].includes(result.status)) {
            this.state.googleIsSync = false;
        } else if (result.status === "no_new_event_from_google" || result.status === "need_refresh") {
            this.state.googleIsSync = true;
        }
        this.state.googleIsPaused = result.status == "sync_paused";
        this.googlePendingSync = false;
        return result;
    },

    get googleCredentialsSet() {
        return this.credentialStatus['google_calendar'] ?? false;
    }
});
