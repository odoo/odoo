odoo.define('microsoft_calendar.CalendarView', function (require) {
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

const MicrosoftCalendarModel = CalendarModel.include({

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
            console.error("Could not synchronize Microsoft events now.", error);
        }
        return _super(...arguments);
    },

    _syncMicrosoftCalendar(shadow = false) {
        return this._rpc({
            route: '/microsoft_calendar/sync_data',
            params: {
                model: this.modelName,
                fromurl: window.location.href,
            }
        }, {shadow});
    },
});

const MicrosoftCalendarController = CalendarController.include({
    custom_events: _.extend({}, CalendarController.prototype.custom_events, {
        syncMicrosoftCalendar: '_onSyncMicrosoftCalendar',
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

        return this.model._syncMicrosoftCalendar().then(function (o) {
            if (o.status === "need_auth") {
                Dialog.alert(self, _t("You will be redirected to Microsoft to authorize the access to your calendar."), {
                    confirm_callback: function() {
                        framework.redirect(o.url);
                    },
                    title: _t('Redirection'),
                });
            } else if (o.status === "need_config_from_admin") {
                if (!_.isUndefined(o.action) && parseInt(o.action)) {
                    Dialog.confirm(self, _t("The Microsoft Synchronization needs to be configured before you can use it, do you want to do it now?"), {
                        confirm_callback: function() {
                            self.do_action(o.action);
                        },
                        title: _t('Configuration'),
                    });
                } else {
                    Dialog.alert(self, _t("An administrator needs to configure Microsoft Synchronization before you can use it!"), {
                        title: _t('Configuration'),
                    });
                }
            } else if (o.status === "need_refresh") {
                self.reload();
            }
        }).then(event.data.on_always, event.data.on_always);
    }
});

const MicrosoftCalendarRenderer = CalendarRenderer.include({
    events: _.extend({}, CalendarRenderer.prototype.events, {
        'click .o_microsoft_sync_button': '_onSyncMicrosoftCalendar',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds the Sync with Microsoft button in the sidebar
     *
     * @private
     */
    _initSidebar: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$microsoftButton = $();
        if (this.model === "calendar.event") {
            this.$microsoftButton = $('<button/>', {type: 'button', html: _t("Sync with <b>Microsoft</b>")})
                                .addClass('o_microsoft_sync_button oe_button btn btn-secondary')
                                .prepend($('<img/>', {
                                    src: "/microsoft_calendar/static/src/img/calendar_outlook_32.png",
                                }))
                                .appendTo(self.$sidebar);
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
        });
    },
});

return {
    MicrosoftCalendarController,
    MicrosoftCalendarModel,
    MicrosoftCalendarRenderer,
};

});
