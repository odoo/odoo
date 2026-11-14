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
     * This override handles the situation where the sync finishes during the initial view load.
     * The sync process can sometimes take a while, so we launch it in the background without awaiting
     * the result so that we don't block the UI.
     *
     * We cannot call 'super.updateData(data)' directly within `syncMicrosoftCalendar` because it
     * could conflict with the update called from the load, leading to inconsistent data.
     * We also cannot call `this.keepLast.add(super.updateData(data));` which would solve that issue
     * by ensuring that only the last update call is kept. If we did so, the original promise would
     * be discarded, and the await in model.js `_load` would never resolve - the view would not load.
     *
     * Instead, we postpone the second update call to the end of the load
     *
     * @override
     */
    async load() {
        this.isLoading = true;
        try {
            await super.load(...arguments);
        } finally {
            this.isLoading = false;
        }
        if (this.updateAfterLoad) {
            this.updateAfterLoad = false;
            await this.postSyncUpdate();
        }
    },

    async postSyncUpdate() {
        if (!this.isAlive()) {
            return;
        }
        const data = { ...this.data };
        await this.keepLast.add(super.updateData(data));
        this.data = data;
        this.notify();
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
        });
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
            if (this.isLoading) {
                this.updateAfterLoad = true;
            } else {
                await this.postSyncUpdate();
            }
        }
        return result;
    },

    get microsoftCredentialsSet() {
        return this.credentialStatus['microsoft_calendar'] ?? false;
    }
});
