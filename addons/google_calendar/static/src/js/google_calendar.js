odoo.define('google_calendar.google_calendar', function (require) {
    "use strict";

    const CalendarRenderer = require('web.CalendarRenderer');
    const CalendarController = require('web.CalendarController');
    const core = require('web.core');
    const Dialog = require('web.Dialog');
    const framework = require('web.framework');
    const utils = require('web.utils');

    const _t = core._t;

    CalendarController.include({
        custom_events: Object.assign({}, CalendarController.prototype.custom_events, {
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
            const self = this;
            const context = this.getSession().user_context;

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
                        confirm_callback: function () {
                            framework.redirect(o.url);
                        },
                        title: _t('Redirection'),
                    });
                } else if (o.status === "need_config_from_admin") {
                    if (o.action !== undefined && parseInt(o.action)) {
                        Dialog.confirm(self, _t("The Google Synchronization needs to be configured before you can use it, do you want to do it now?"), {
                            confirm_callback: function () {
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
                    const confirmText1 = _t(`The account you are trying to synchronize (${o.info.new_name}) is not the same as the last one used (${o.info.old_name})!`);
                    const confirmText2 = _t("In order to do this, you first need to disconnect all existing events from the old account.");
                    const confirmText3 = _t("Do you want to do this now?");
                    const text = `${confirmText1}\n${confirmText2}\n\n${confirmText3}`;
                    Dialog.confirm(self, text, {
                        confirm_callback: function () {
                            self._rpc({
                                    route: '/google_calendar/remove_references',
                                    params: {
                                        model: self.state.model,
                                        local_context: context,
                                    },
                                })
                                .then(function (o) {
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
            }).then(event.data.on_always, event.data.on_always);
        }
    });

    utils.patch(CalendarRenderer, 'google_calendar.google_calendar', {

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Requests to sync the calendar with Google Calendar
         *
         * @private
         */
        _onSyncCalendar() {
            const googleButton = this.el.querySelector('.o_google_sync_button');
            googleButton.disabled = true;
            this.trigger('syncCalendar', {
                on_always: () => {
                    googleButton.disabled = false;
                },
            });
        },
    });

});
