odoo.define('google_calendar.google_calendar', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var CalendarRenderer = require('web.CalendarRenderer');
var CalendarController = require('web.CalendarController');

var _t = core._t;

CalendarController.include({
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
        var context = this.getSession().user_context;

        this._rpc({
            route: '/google_calendar/sync_data',
            params: {
                model: this.modelName,
                fromurl: window.location.href,
                local_context: context,
            }
        }).then(function (o) {
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
            } else if (o.status === "need_reset") {
                var confirmText1 = _t("The account you are trying to synchronize (%s) is not the same as the last one used (%s)!");
                var confirmText2 = _t("In order to do this, you first need to disconnect all existing events from the old account.");
                var confirmText3 = _t("Do you want to do this now?");
                var text = _.str.sprintf(confirmText1 + "\n" + confirmText2 + "\n\n" + confirmText3, o.info.new_name, o.info.old_name);
                Dialog.confirm(self, text, {
                    confirm_callback: function() {
                        self._rpc({
                                route: '/google_calendar/remove_references',
                                params: {
                                    model: self.state.model,
                                    local_context: context,
                                },
                            })
                            .done(function(o) {
                                if (o.status === "OK") {
                                    Dialog.alert(self, _t("All events have been disconnected from your previous account. You can now restart the synchronization"), {
                                        title: _t('Event disconnection success'),
                                    });
                                } else if (o.status === "KO") {
                                    Dialog.alert(self, _t("An error occured while disconnecting events from your previous account. Please retry or contact your administrator."), {
                                        title: _t('Event disconnection error'),
                                    });
                                } // else NOP
                            });
                    },
                    title: _t('Accounts'),
                });
            }
        }).always(function () {
            event.data.on_always();
        });
    }
});

CalendarRenderer.include({
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

});
