import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { user } from "@web/core/user";

patch(AttendeeCalendarModel, {
    services: [...AttendeeCalendarModel.services],
});

patch(AttendeeCalendarModel.prototype, {
    setup(params) {
        super.setup(...arguments);
        this.isAlive = params.isAlive;
        this.microsoftSyncTimedOut = false;
        this.state = useState({
            microsoftSyncResetting: false,
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

    async syncMicrosoftCalendar(silent = false, force_auth = false) {
        this.state.microsoftPendingSync = true;

        const [{microsoft_synchronization_needs_reset}] = await this.orm.read(
            "res.users",
            [user.userId],
            ["microsoft_synchronization_needs_reset"],
        );
        if (microsoft_synchronization_needs_reset) {
            this.state.microsoftSyncResetting = true;
            await this.orm.call(
                "res.users",
                "restart_microsoft_synchronization",
                [[user.userId]],
            );
            this.state.microsoftSyncResetting = false;
        }

        const result = await rpc(
            "/microsoft_calendar/sync_data",
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
            this.state.microsoftIsSync = false;
        } else if (result.status === "no_new_event_from_microsoft" || result.status === "need_refresh") {
            this.state.microsoftIsSync = true;
        }
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
