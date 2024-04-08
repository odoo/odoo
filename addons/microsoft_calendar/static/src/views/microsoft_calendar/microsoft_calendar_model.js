/** @odoo-module **/

import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel, "microsoft_calendar_microsoft_calendar_model", {
    services: [...AttendeeCalendarModel.services, "rpc"],
});

patch(AttendeeCalendarModel.prototype, "microsoft_calendar_microsoft_calendar_model_functions", {
    setup(params, { rpc }) {
        this._super(...arguments);
        this.rpc = rpc;
        this.isAlive = params.isAlive;
        this.microsoftIsSync = true;
        this.microsoftPendingSync = false;
    },

    /**
     * @override
     */
    async updateData() {
        const _super = this._super.bind(this);
        if (this.microsoftPendingSync) {
            return _super(...arguments);
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
        if (this.isAlive()) {
            return _super(...arguments);
        }
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
        if (["need_config_from_admin", "need_auth", "sync_stopped"].includes(result.status)) {
            this.microsoftIsSync = false;
        } else if (result.status === "no_new_event_from_microsoft" || result.status === "need_refresh") {
            this.microsoftIsSync = true;
        }
        this.microsoftPendingSync = false;
        return result;
    },
});
