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
        this.microsoftIsSync = true;
        this.microsoftPendingSync = false;
        this.microsoftIsPaused = false;
    },

    /**
     * @override
     */
    async updateData() {
        if (this.microsoftPendingSync) {
            return super.updateData(...arguments);
        }
        try {
            await Promise.race([
                new Promise(resolve => setTimeout(resolve, 1000)),
                this.syncMicrosoftCalendar(true)
            ]);
        } catch (error) {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize microsoft events now.", error);
            this.microsoftPendingSync = false;
        }
        return super.updateData(...arguments);
    },

    async syncMicrosoftCalendar(silent = false) {
        this.microsoftPendingSync = true;
        const result = await this.rpc(
            "/microsoft_calendar/sync_data",
            {
                model: this.resModel,
                fromurl: window.location.href
            },
            {
                silent,
            },
        );
        if (["need_config_from_admin", "need_auth", "sync_stopped", "sync_paused"].includes(result.status)) {
            this.microsoftIsSync = false;
        } else if (result.status === "no_new_event_from_microsoft" || result.status === "need_refresh") {
            this.microsoftIsSync = true;
        }
        this.microsoftIsPaused = result.status == "sync_paused";
        this.microsoftPendingSync = false;
        return result;
    },
});
