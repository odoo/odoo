odoo.define('google_calendar.CalendarView', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
const CalendarView = require('calendar.CalendarView');
const CalendarRenderer = require('calendar.CalendarRenderer');
const CalendarController = require('calendar.CalendarController');
const CalendarModel = require('calendar.CalendarModel');
const viewRegistry = require('web.view_registry');
const session = require('web.session');

var _t = core._t;

const GoogleCalendarModel = CalendarModel.include({

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.google_is_sync = true;
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
        }
        return _super(...arguments);
    },

    _syncGoogleCalendar(shadow = false) {
        var self = this;
        var context = this.getSession().user_context;
        return this._rpc({
            route: '/google_calendar/sync_data',
            params: {
                model: this.modelName,
                fromurl: window.location.href,
                local_context: context, // LUL TODO remove this local_context
            }
        }, {shadow}).then(function (result) {
            if (["need_config_from_admin", "need_auth", "sync_stopped"].includes(result.status)) {
                self.google_is_sync = false;
            } else if (result.status === "no_new_event_from_google" || result.status === "need_refresh") {
                self.google_is_sync = true;
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
                Dialog.alert(self, _t("You will be redirected to Google to authorize access to your calendar!"), {
                    confirm_callback: function() {
                        framework.redirect(o.url);
                    },
                    title: _t('Redirection'),
                });
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

    _onArchiveRecord: function (event) {
        var self = this;
        Dialog.confirm(this, _t("Are you sure you want to archive this record ?"), {
            confirm_callback: function () {
                self.model.archiveRecords([event.data.id], self.modelName).then(function () {
                    self.reload();
                });
            }
        });
    },
});

const GoogleCalendarRenderer = CalendarRenderer.include({
    custom_events: _.extend({}, CalendarRenderer.prototype.custom_events, {
        archive_event: '_onArchiveEvent',
    }),

    events: _.extend({}, CalendarRenderer.prototype.events, {
        'click .o_google_sync_button': '_onGoogleSyncCalendar',
        'click .o_stop_google_sync_button': '_onStopGoogleSynchronization',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _initGooglePillButton: function() {
        this.$googleStopButton.css({"cursor":"pointer", "font-size":"0.9em"});
        var switchBadgeClass = (elem) => {elem.toggleClass('badge-success'); elem.toggleClass('badge-danger');};
        this.$('.o_stop_google_sync_button').hover(() => {
            switchBadgeClass(this.$googleStopButton);
            this.$googleStopButton.html("<i class='fa mr-2 fa-times'/>".concat(_t("Stop the Synchronization")));
        }, () => {
            switchBadgeClass(this.$googleStopButton);
            this.$googleStopButton.html("<i class='fa mr-2 fa-check'/>".concat(_t("Synched with Google")));
        });
    },

    _getGoogleButton: function () {
        return $('<button/>', {
            type: 'button',
            html: _t("Sync with <b>Google</b>"),
            class: 'o_google_sync_button w-100 m-auto btn btn-secondary'
        });
    },

    _getGoogleStopButton: function () {
        return  $('<span/>', {
            html: _t("Synched with Google"),
            class: 'w-100 badge badge-pill badge-success border-0 o_stop_google_sync_button'
        })
        .prepend($('<i/>', {class: "fa mr-2 fa-check"}));
    },

    /**
     * Adds the Sync with Google button in the sidebar
     *
     * @private
     */
    _initSidebar: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$googleButton = $();
        this.$googleStopButton = $();
        if (this.model === "calendar.event") {
            if (this.state.google_is_sync) {
                this.$googleStopButton = this._getGoogleStopButton().appendTo(self.$sidebar);
                this._initGooglePillButton();
            } else {
                this.$googleButton = this._getGoogleButton().appendTo(self.$sidebar);
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
        var context = this.getSession().user_context;
        this.$googleButton.prop('disabled', true);
        this.trigger_up('syncGoogleCalendar', {
            on_always: function () {
                self.$googleButton.prop('disabled', false);
            },
            on_refresh: function () {
                if (_.isEmpty(self.$googleStopButton)) {
                    self.$googleStopButton = self._getGoogleStopButton();
                }
                self.$googleButton.replaceWith(self.$googleStopButton);
                self._initGooglePillButton();
            }
        });
    },

    _onStopGoogleSynchronization: function() {
        var self = this;
        this.$googleStopButton.prop('disabled', true);
        this.trigger_up('stopGoogleSynchronization' , {
            on_confirm: function () {
                if (_.isEmpty(self.$googleButton)) {
                    self.$googleButton = self._getGoogleButton();
                }
                self.$googleStopButton.replaceWith(self.$googleButton);
            },
            on_always: function() {
                self.$googleStopButton.prop('disabled', false);
            }
        });
    },

    _onArchiveEvent: function (event) {
        this._unselectEvent();
        this.trigger_up('archiveRecord', {id: parseInt(event.data.id, 10)});
    },
});

return {
    GoogleCalendarController,
    GoogleCalendarModel,
    GoogleCalendarRenderer,
};

});
