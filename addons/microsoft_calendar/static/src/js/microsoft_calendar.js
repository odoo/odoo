odoo.define('microsoft_calendar.CalendarView', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
const CalendarView = require('@calendar/js/calendar_view')[Symbol.for("default")];
const CalendarRenderer = require('@calendar/js/calendar_renderer')[Symbol.for("default")].AttendeeCalendarRenderer;
const CalendarController = require('@calendar/js/calendar_controller')[Symbol.for("default")];
const CalendarModel = require('@calendar/js/calendar_model')[Symbol.for("default")];
const viewRegistry = require('web.view_registry');
const session = require('web.session');

var _t = core._t;

const MicrosoftCalendarModel = CalendarModel.include({

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.microsoft_is_sync = true;
    },

    /**
     * @override
     */
    __get: function () {
        var result = this._super.apply(this, arguments);
        result.microsoft_is_sync = this.microsoft_is_sync;
        return result;
    },

    /**
     * @override
     * @returns {Promise}
     */
    async _loadCalendar() {
        const _super = this._super.bind(this);
        try {
            await Promise.race([
                new Promise(resolve => setTimeout(resolve, 1000)),
                this._syncMicrosoftCalendar(true)
            ]);
        } catch (error) {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize Outlook events now.", error);
        }
        return _super(...arguments);
    },

    _syncMicrosoftCalendar(shadow = false) {
        var self = this;
        return this._rpc({
            route: '/microsoft_calendar/sync_data',
            params: {
                model: this.modelName,
                fromurl: window.location.href,
            }
        }, {shadow}).then(function (result) {
            if (["need_config_from_admin", "need_auth", "sync_stopped"].includes(result.status)) {
                self.microsoft_is_sync = false;
            } else if (result.status === "no_new_event_from_microsoft" || result.status === "need_refresh") {
                self.microsoft_is_sync = true;
            }
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
});

const MicrosoftCalendarController = CalendarController.include({
    custom_events: _.extend({}, CalendarController.prototype.custom_events, {
        syncMicrosoftCalendar: '_onSyncMicrosoftCalendar',
        stopMicrosoftSynchronization: '_onStopMicrosoftSynchronization',
        archiveRecord: '_onArchiveRecord',
    }),


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Try to sync the calendar with Microsoft Calendar. According to the result
     * from Microsoft API, this function may require an action of the user by the
     * mean of a dialog.
     *
     * @private
     * @returns {OdooEvent} event
     */
    _onSyncMicrosoftCalendar: function (event) {
        var self = this;

        return this._restartMicrosoftSynchronization().then(() => {return this.model._syncMicrosoftCalendar();}).then(function (o) {
            if (o.status === "need_auth") {
                Dialog.alert(self, _t("You will be redirected to Outlook to authorize the access to your calendar."), {
                    confirm_callback: function() {
                        framework.redirect(o.url);
                    },
                    title: _t('Redirection'),
                });
            } else if (o.status === "need_config_from_admin") {
                if (!_.isUndefined(o.action) && parseInt(o.action)) {
                    Dialog.confirm(self, _t("The Outlook Synchronization needs to be configured before you can use it, do you want to do it now?"), {
                        confirm_callback: function() {
                            self.do_action(o.action);
                        },
                        title: _t('Configuration'),
                    });
                } else {
                    Dialog.alert(self, _t("An administrator needs to configure Outlook Synchronization before you can use it!"), {
                        title: _t('Configuration'),
                    });
                }
            } else if (o.status === "need_refresh") {
                self.reload();
                return event.data.on_refresh();
            }
        }).then(event.data.on_always, event.data.on_always);
    },

    _onStopMicrosoftSynchronization: function (event) {
        var self = this;
        Dialog.confirm(this, _t("You are about to stop the synchronization of your calendar with Outlook. Are you sure you want to continue?"), {
            confirm_callback: function() {
                return self._rpc({
                    model: 'res.users',
                    method: 'stop_microsoft_synchronization',
                    args: [[self.context.uid]],
                }).then(() => {
                    self.displayNotification({
                        title: _t("Success"),
                        message: _t("The synchronization with Outlook calendar was successfully stopped."),
                        type: 'success',
                    });
                }).then(event.data.on_confirm);
            },
            title: _t('Confirmation'),
        });

        return event.data.on_always();
    },

    _restartMicrosoftSynchronization: function () {
        return this._rpc({
            model: 'res.users',
            method: 'restart_microsoft_synchronization',
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

const MicrosoftCalendarRenderer = CalendarRenderer.include({
    custom_events: _.extend({}, CalendarRenderer.prototype.custom_events, {
        archive_event: '_onArchiveEvent',
    }),

    events: _.extend({}, CalendarRenderer.prototype.events, {
        'click .o_microsoft_sync_pending': '_onSyncMicrosoftCalendar',
        'click .o_microsoft_sync_button_configured': '_onStopMicrosoftSynchronization',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _initMicrosoftPillButton: function() {
        // hide the pending button
        this.$calendarSyncContainer.find('#microsoft_sync_pending').hide();
        const switchBadgeClass = elem => elem.toggleClass(['badge-primary', 'badge-danger']);
        this.$('#microsoft_sync_configured').hover(() => {
            switchBadgeClass(this.$calendarSyncContainer.find('#microsoft_sync_configured'));
            this.$calendarSyncContainer.find('#microsoft_check').hide();
            this.$calendarSyncContainer.find('#microsoft_stop').show();
        }, () => {
            switchBadgeClass(this.$calendarSyncContainer.find('#microsoft_sync_configured'));
            this.$calendarSyncContainer.find('#microsoft_stop').hide();
            this.$calendarSyncContainer.find('#microsoft_check').show();
        });
    },

    _getMicrosoftButton: function () {
        this.$calendarSyncContainer.find('#microsoft_sync_configured').hide();
        this.$calendarSyncContainer.find('#microsoft_sync_pending').show();
    },

    _getMicrosoftStopButton: function () {
        this.$calendarSyncContainer.find('#microsoft_sync_configured').show();
        this.$calendarSyncContainer.find('#microsoft_sync_pending').hide();
    },

    /**
     * Adds the Sync with Outlook button in the sidebar
     *
     * @private
     */
    _initSidebar: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$microsoftButton = this.$('#microsoft_sync_pending');
        this.$microsoftStopButton = this.$('#microsoft_sync_configured');
        if (this.model === "calendar.event") {
            if (this.state.microsoft_is_sync) {
                this._initMicrosoftPillButton();
            } else {
                // Hide the button needed when the calendar sync is configured
                self.$microsoftStopButton.hide();
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Requests to sync the calendar with Microsoft Calendar
     *
     * @private
     */
    _onSyncMicrosoftCalendar: function () {
        var self = this;
        var context = this.getSession().user_context;
        this.$microsoftButton.prop('disabled', true);
        this.trigger_up('syncMicrosoftCalendar', {
            on_always: function () {
                self.$microsoftButton.prop('disabled', false);
            },
            on_refresh: function () {
                self._initMicrosoftPillButton();
            }
        });
    },

    _onStopMicrosoftSynchronization: function() {
        var self = this;
        this.$microsoftStopButton.prop('disabled', true);
        this.trigger_up('stopMicrosoftSynchronization' , {
            on_confirm: function () {
                self.$microsoftStopButton.hide();
                self.$microsoftButton.show();
            },
            on_always: function() {
                self.$microsoftStopButton.prop('disabled', false);
            }
        });
    },

    _onArchiveEvent: function (event) {
        this._unselectEvent();
        this.trigger_up('archiveRecord', {id: parseInt(event.data.id, 10), event: event.target.event.extendedProps});
    },
});

return {
    MicrosoftCalendarController,
    MicrosoftCalendarModel,
    MicrosoftCalendarRenderer,
};

});
