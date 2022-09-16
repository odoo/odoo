odoo.define('google_calendar.CalendarView', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
const CalendarRenderer = require('@calendar/js/calendar_renderer')[Symbol.for("default")].AttendeeCalendarRenderer;
const CalendarController = require('@calendar/js/calendar_controller')[Symbol.for("default")];
const CalendarModel = require('@calendar/js/calendar_model')[Symbol.for("default")];
const session = require('web.session');

var _t = core._t;

const GoogleCalendarModel = CalendarModel.include({

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.google_is_sync = true;
        this.google_pending_sync = false;
    },

    /**
     * @override
     */
    __get: function () {
        var result = this._super.apply(this, arguments);
        result.google_is_sync = this.google_is_sync;
        return result;
    },


    /**
     * @override
     * @returns {Promise}
     */
    async _loadCalendar() {
        const _super = this._super.bind(this);
        // When the calendar synchronization takes some time, prevents retriggering the sync while navigating the calendar.
        if (this.google_pending_sync) {
            return _super(...arguments);
        }
        try {
            await Promise.race([
                new Promise(resolve => setTimeout(resolve, 1000)),
                this._syncGoogleCalendar(true)
            ]);
        } catch (error) {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize Google events now.", error);
            this.google_pending_sync = false;
        }
        return _super(...arguments);
    },

    _syncGoogleCalendar(shadow = false) {
        var self = this;
        this.google_pending_sync = true;
        return this._rpc({
            route: '/google_calendar/sync_data',
            params: {
                model: this.modelName,
                fromurl: window.location.href,
            }
        }, {shadow}).then(function (result) {
            if (["need_config_from_admin", "need_auth", "sync_stopped"].includes(result.status)) {
                self.google_is_sync = false;
            } else if (result.status === "no_new_event_from_google" || result.status === "need_refresh") {
                self.google_is_sync = true;
            }
            self.google_pending_sync = false;
            return result
        });
    },

    archiveRecords: function (ids, model) {
        return this._rpc({
                model: model,
                method: 'action_archive',
                args: [ids],
                context: session.user_context,
            });
    },
})

const GoogleCalendarController = CalendarController.include({
    custom_events: _.extend({}, CalendarController.prototype.custom_events, {
        syncGoogleCalendar: '_onGoogleSyncCalendar',
        stopGoogleSynchronization: '_onStopGoogleSynchronization',
        archiveRecord: '_onArchiveRecord',
    }),


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Try to sync the calendar with Google Calendar. According to the result
     * from Google API, this function may require an action of the user by the
     * mean of a dialog.
     *
     * @private
     * @returns {OdooEvent} event
     */
    _onGoogleSyncCalendar: function (event) {
        var self = this;

        return this._restartGoogleSynchronization().then(() => {return this.model._syncGoogleCalendar();}).then(function (o) {
            if (o.status === "need_auth") {
                // allows to configure API keys in modal and will then redirect.
                self.renderer._configureCalendarProviderSync('google');
            } else if (o.status === "need_config_from_admin") {
                if (!_.isUndefined(o.action) && parseInt(o.action)) {
                    Dialog.confirm(self, _t("The Google Synchronization needs to be configured before you can use it, do you want to do it now?"), {
                        confirm_callback: function() {
                            self.do_action(o.action);
                        },
                        title: _t('Configuration'),
                    });
                } else {
                    Dialog.alert(self, _t("An administrator needs to configure Google Synchronization before you can use it!"), {
                        title: _t('Configuration'),
                    });
                }
            } else if (o.status === "need_refresh") {
                self.reload();
                return event.data.on_refresh();
            }
        }).then(event.data.on_always, event.data.on_always);
    },

    _onStopGoogleSynchronization: function (event) {
        var self = this;
        Dialog.confirm(this, _t("You are about to stop the synchronization of your calendar with Google. Are you sure you want to continue?"), {
            confirm_callback: function() {
                return self._rpc({
                    model: 'res.users',
                    method: 'stop_google_synchronization',
                    args: [[self.context.uid]],
                }).then(() => {
                    self.displayNotification({
                        title: _t("Success"),
                        message: _t("The synchronization with Google calendar was successfully stopped."),
                        type: 'success',
                    });
                }).then(event.data.on_confirm);
            },
            title: _t('Confirmation'),
        });

        return event.data.on_always();
    },

    _restartGoogleSynchronization: function () {
        return this._rpc({
            model: 'res.users',
            method: 'restart_google_synchronization',
            args: [[this.context.uid]],
        });
    },

    _onArchiveRecord: async function (event) {
        const self = this;
        if (event.data.event.record.recurrency) {
            const recurrenceUpdate = await this._askRecurrenceUpdatePolicy();
            event.data = Object.assign({}, event.data, {
                    'recurrenceUpdate': recurrenceUpdate,
                });
                if (recurrenceUpdate === 'self_only') {
                    self.model.archiveRecords([event.data.id], self.modelName).then(function () {
                    self.reload();
                });
                } else {
                    return this._rpc({
                        model: self.modelName,
                        method: 'action_mass_archive',
                        args: [[event.data.id], recurrenceUpdate],
                    }).then( function () {
                        self.reload();
                    });
                }
        } else {
            Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
                confirm_callback: function () {
                    self.model.archiveRecords([event.data.id], self.modelName).then(function () {
                        self.reload();
                    });
                }
            });
        }
    },
});

const GoogleCalendarRenderer = CalendarRenderer.include({
    custom_events: _.extend({}, CalendarRenderer.prototype.custom_events, {
        archive_event: '_onArchiveEvent',
    }),

    events: _.extend({}, CalendarRenderer.prototype.events, {
        'click .o_google_sync_pending': '_onGoogleSyncCalendar',
        'click .o_google_sync_button_configured': '_onStopGoogleSynchronization',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _initGooglePillButton: function() {
        // hide the pending button
        this.$calendarSyncContainer.find('#google_sync_pending').hide();
        const switchBadgeClass = elem => elem.toggleClass(['bg-primary', 'bg-danger']);
        this.$('#google_sync_configured').hover(() => {
            switchBadgeClass(this.$calendarSyncContainer.find('#google_sync_configured'));
            this.$calendarSyncContainer.find('#google_check').hide();
            this.$calendarSyncContainer.find('#google_stop').show();
        }, () => {
            switchBadgeClass(this.$calendarSyncContainer.find('#google_sync_configured'));
            this.$calendarSyncContainer.find('#google_stop').hide();
            this.$calendarSyncContainer.find('#google_check').show();
        });
    },

    _getGoogleButton: function () {
        this.$calendarSyncContainer.find('#google_sync_pending').show();
    },

    _getGoogleStopButton: function () {
        this.$calendarSyncContainer.find('#google_sync_configured').show();
    },

    /**
     * Adds the Sync with Google button in the sidebar
     *
     * @private
     */
    _initSidebar: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$googleButton = this.$('#google_sync_pending');
        this.$googleStopButton = this.$('#google_sync_configured');
        if (this.model === "calendar.event") {
            if (this.state.google_is_sync) {
                this._initGooglePillButton();
            } else {
                // Hide the button needed when the calendar sync is configured
                self.$googleStopButton.hide();
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Requests to sync the calendar with Google Calendar
     *
     * @private
     */
    _onGoogleSyncCalendar: function () {
        var self = this;
        this.$googleButton.prop('disabled', true);
        this.trigger_up('syncGoogleCalendar', {
            on_always: function () {
                self.$googleButton.prop('disabled', false);
            },
            on_refresh: function () {
                self._initGooglePillButton();
            }
        });
    },

    _onStopGoogleSynchronization: function() {
        var self = this;
        this.$googleStopButton.prop('disabled', true);
        this.trigger_up('stopGoogleSynchronization' , {
            on_confirm: function () {
                self.$googleStopButton.hide();
                self.$googleButton.show();
            },
            on_always: function() {
                self.$googleStopButton.prop('disabled', false);
            }
        });
    },

    _onArchiveEvent: function (event) {
        this._unselectEvent();
        this.trigger_up('archiveRecord', {id: parseInt(event.data.id, 10), event: event.target.event.extendedProps});
    },
});

return {
    GoogleCalendarController,
    GoogleCalendarModel,
    GoogleCalendarRenderer,
};

});
