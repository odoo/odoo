/** @odoo-module **/

import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel, "google_calendar_google_calendar_model", {
    services: [...AttendeeCalendarModel.services, "rpc"],
});

patch(AttendeeCalendarModel.prototype, "google_calendar_google_calendar_model_functions", {
    setup(params, { rpc }) {
        this._super(...arguments);
        this.rpc = rpc;
        this.googleIsSync = true;
        this.googlePendingSync = false;
    },

    /**
     * @override
     */
    async updateData() {
        const _super = this._super.bind(this);
        if (this.googlePendingSync) {
            return _super(...arguments);
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
        return _super(...arguments);
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
        if (["need_config_from_admin", "need_auth", "sync_stopped"].includes(result.status)) {
            this.googleIsSync = false;
        } else if (result.status === "no_new_event_from_google" || result.status === "need_refresh") {
            this.googleIsSync = true;
        }
        this.googlePendingSync = false;
        return result;
    },
});
