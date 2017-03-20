odoo.define('google_calendar.google_calendar', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var CalendarRenderer = require('web.CalendarRenderer');

var _t = core._t;

CalendarRenderer.include({
    events: _.extend({}, CalendarRenderer.prototype.events, {
        'click .o_google_sync_button': function () {
            this.syncCalendar(this.fields_view);
        }
    }),
    syncCalendar: function() {
        var self = this;
        var context = this.getSession().user_context;
        this.$google_button.prop('disabled', true);

        this.trigger_up('perform_rpc', {
            route: '/google_calendar/sync_data',
            args: {
                model: this.state.model,
                fromurl: window.location.href,
                local_context: context,
            },
            on_success: function (o) {
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
                    self.$calendar.fullCalendar('refetchEvents');
                } else if (o.status === "need_reset") {
                    var confirm_text1 = _t("The account you are trying to synchronize (%s) is not the same as the last one used (%s)!");
                    var confirm_text2 = _t("In order to do this, you first need to disconnect all existing events from the old account.");
                    var confirm_text3 = _t("Do you want to do this now?");
                    var text = _.str.sprintf(confirm_text1 + "\n" + confirm_text2 + "\n\n" + confirm_text3, o.info.new_name, o.info.old_name);
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

                self.$google_button.prop('disabled', false);
            },
        });
    },
    initSidebar: function() {
        var self = this;
        this._super();
        this.$google_button = $();
        if (this.state.model === "calendar.event") {
            this.$google_button = $('<button/>', {type: 'button', html: _t("Sync with <b>Google</b>")})
                                .addClass('o_google_sync_button oe_button btn btn-sm btn-default')
                                .prepend($('<img/>', {
                                    src: "/google_calendar/static/src/img/calendar_32.png",
                                }))
                                .appendTo(self.$('.o_calendar_sidebar'));
        }
    },
});

});
