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

var _t = core._t;

const GoogleCalendarModel = CalendarModel.extend({

    /**
     * @override
     * @returns {Promise}
     */
    async _loadCalendar() {
        const _super = this._super.bind(this);
        try {
            await Promise.race([
                new Promise(resolve => setTimeout(resolve, 1000)),
                this._syncCalendar(true)
            ]);
        } catch (error) {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize Google events now.", error);
        }
        return _super(...arguments);
    },

    _syncCalendar(shadow = false) {
        var context = this.getSession().user_context;
        return this._rpc({
            route: '/google_calendar/sync_data',
            params: {
                model: this.modelName,
                fromurl: window.location.href,
                local_context: context, // LUL TODO remove this local_context
            }
        }, {shadow});
    },
})

const GoogleCalendarController = CalendarController.extend({
    custom_events: _.extend({}, CalendarController.prototype.custom_events, {
        syncCalendar: '_onSyncCalendar',
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
    _onSyncCalendar: function (event) {
        var self = this;

        return this.model._syncCalendar().then(function (o) {
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
    }
});

const GoogleCalendarRenderer = CalendarRenderer.extend({
    events: _.extend({}, CalendarRenderer.prototype.events, {
        'click .o_google_sync_button': '_onSyncCalendar',
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
            this.$googleButton = $('<button/>', {type: 'button', html: _t("Sync with <b>Google</b>")})
                                .addClass('o_google_sync_button oe_button btn btn-secondary')
                                .prepend($('<img/>', {
                                    src: "/google_calendar/static/src/img/calendar_32.png",
                                }))
                                .appendTo(self.$sidebar);
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
    _onSyncCalendar: function () {
        var self = this;
        var context = this.getSession().user_context;
        this.$googleButton.prop('disabled', true);
        this.trigger_up('syncCalendar', {
            on_always: function () {
                self.$googleButton.prop('disabled', false);
            },
        });
    },
});

var GoogleCalendarView = CalendarView.extend({
    config: _.extend({}, CalendarView.prototype.config, {
        Controller: GoogleCalendarController,
        Model: GoogleCalendarModel,
        Renderer: GoogleCalendarRenderer,
    }),
});

viewRegistry.add('google_sync_calendar', GoogleCalendarView);

return {
    GoogleCalendarView,
    GoogleCalendarController,
    GoogleCalendarModel,
    GoogleCalendarRenderer,
};

});
