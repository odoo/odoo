import { proxy } from "@odoo/owl";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(AttendeeCalendarModel.prototype, {
    setup(params) {
        super.setup(...arguments);
        this.isAlive = params.isAlive;
        this.state = proxy({
            googlePendingSync: false,
            googleIsSync: true,
            googleIsPaused: false,
            googleSyncError: false,
        });
    },

    /** Override
     * This override handles the situation where the sync finishes during the initial view load.
     * The sync process can sometimes take a while, so we launch it in the background without awaiting
     * the result so that we don't block the UI.
     *
     * We cannot call 'super.updateData(data)' directly within `syncGoogleCalendar` because it could
     * conflict with the update called from the load, leading to inconsistent data.
     * We also cannot call `this.keepLast.add(super.updateData(data));` which would solve that issue
     * by ensuring that only the last update call is kept. If we did so, the original promise would
     * be discarded, and the await in model.js `_load` would never resolve - the view would not load.
     *
     * Instead, we postpone the second update call to the end of the load
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
    async updateData(data) {
        if (this.state.googlePendingSync) {
            await super.updateData(...arguments);
            return this.updateCalendarData(data);
        }
        this.syncGoogleCalendar(true).catch((error) => {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize Google events now.", error);
            this.state.googlePendingSync = false;
        })
        if (this.isAlive()) {
            await super.updateData(...arguments);
            return this.updateCalendarData(data);
        }
        return new Promise(() => {});
    },

    async updateCalendarData(data) {
        for (const event of Object.values(data.records)) {
            event.isInUserCalendars = this.calendarIds?.includes(event.rawRecord.calendar_id[0]);
        }
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
        if (result.status === "need_refresh") {
            if (this.isLoading) {
                this.updateAfterLoad = true;
            } else {
                await this.postSyncUpdate();
            }
        }
        if (result.new_calendars) {
            this.notification.add(
                _t("New Google calendars detected"),
                {
                    type: "info",
                    buttons: [{
                        name: _t("Choose which ones to synchronize"),
                        onClick: () => this.action.doAction('calendar.action_calendar_calendar'),
                    }],
                },
            );
        }
        return result;
    },

    get googleCredentialsSet() {
        return this.credentialStatus['google_calendar'] ?? false;
    }
});
