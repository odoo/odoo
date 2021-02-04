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
            if (result.status === "need_config_from_admin" || result.status === "need_auth") {
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

        return this.model._syncGoogleCalendar().then(function (o) {
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
            }
        }).then(event.data.on_always, event.data.on_always);
    },

    _onArchiveRecord: function (ev) {
        var self = this;
        Dialog.confirm(this, _t("Are you sure you want to archive this record ?"), {
            confirm_callback: function () {
                self.model.archiveRecords([ev.data.id], self.modelName).then(function () {
                    self.reload();
                });
            }
        });
    },
});

const GoogleCalendarRenderer = CalendarRenderer.include({
    events: _.extend({}, CalendarRenderer.prototype.events, {
        'click .o_google_sync_button': '_onGoogleSyncCalendar',
    }),
    
    custom_events: _.extend({}, CalendarRenderer.prototype.custom_events, {
        archive_event: '_onArchiveEvent',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds the Sync with Google button in the sidebar
     *
     * @private
     */
    _initSidebar: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$googleButton = $();
        if (this.model === "calendar.event") {
            if (this.state.google_is_sync) {
                this.$googleButton = $('<span/>', {html: _t("Synched with Google")})
                                .addClass('o_google_sync badge badge-pill badge-success')
                                .prepend($('<i/>', {class: "fa mr-2 fa-check"}))
                                .appendTo(self.$sidebar);
            } else {
                this.$googleButton = $('<button/>', {type: 'button', html: _t("Sync with <b>Google</b>")})
                                .addClass('o_google_sync_button oe_button btn btn-secondary')
                                .appendTo(self.$sidebar);
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
        });
    },

    _onArchiveEvent: function (ev) {
        this._unselectEvent();
        this.trigger_up('archiveRecord', {id: parseInt(ev.data.id, 10)});
    }
});

return {
    GoogleCalendarController,
    GoogleCalendarModel,
    GoogleCalendarRenderer,
};

});
