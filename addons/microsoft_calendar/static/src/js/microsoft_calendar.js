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

const MicrosoftCalendarRenderer = CalendarRenderer.include({
    custom_events: _.extend({}, CalendarRenderer.prototype.custom_events, {
        archive_event: '_onArchiveEvent',
    }),

    events: _.extend({}, CalendarRenderer.prototype.events, {
        'click .o_microsoft_sync_button': '_onSyncMicrosoftCalendar',
        'click .o_stop_microsoft_sync_button': '_onStopMicrosoftSynchronization',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _initMicrosoftPillButton: function() {
        this.$microsoftStopButton.css({"cursor":"pointer", "font-size":"0.9em"});
        var switchBadgeClass = (elem) => {elem.toggleClass('badge-primary'); elem.toggleClass('badge-danger');};
        this.$('.o_stop_microsoft_sync_button').hover(() => {
            switchBadgeClass(this.$microsoftStopButton);
            this.$microsoftStopButton.html("<i class='fa mr-2 fa-times'/>".concat(_t("Stop the Synchronization")));
        }, () => {
            switchBadgeClass(this.$microsoftStopButton);
            this.$microsoftStopButton.html("<i class='fa mr-2 fa-check'/>".concat(_t("Synched with Outlook")));
        });
    },

    _getMicrosoftButton: function () {
        return $('<button/>', {
            type: 'button',
            html: _t("Sync with <b>Outlook</b>"),
            class: 'o_microsoft_sync_button w-100 m-auto btn btn-secondary'
        });
    },

    _getMicrosoftStopButton: function () {
        return  $('<span/>', {
            html: _t("Synched with Outlook"),
            class: 'w-100 badge badge-pill badge-primary border-0 o_stop_microsoft_sync_button'
        })
        .prepend($('<i/>', {class: "fa mr-2 fa-check"}));
    },

    /**
     * Adds the Sync with Outlook button in the sidebar
     *
     * @private
     */
    _initSidebar: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$microsoftButton = $();
        this.$microsoftStopButton = $();
        if (this.model === "calendar.event") {
            if (this.state.microsoft_is_sync) {
                this.$microsoftStopButton = this._getMicrosoftStopButton().appendTo(self.$sidebar);
                this._initMicrosoftPillButton();
            } else {
                this.$microsoftButton = this._getMicrosoftButton().appendTo(self.$sidebar);
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
                if (_.isEmpty(self.$microsoftStopButton)) {
                    self.$microsoftStopButton = self._getMicrosoftStopButton();
                }
                self.$microsoftButton.replaceWith(self.$microsoftStopButton);
                self._initMicrosoftPillButton();
            }
        });
    },

    _onStopMicrosoftSynchronization: function() {
        var self = this;
        this.$microsoftStopButton.prop('disabled', true);
        this.trigger_up('stopMicrosoftSynchronization' , {
            on_confirm: function () {
                if (_.isEmpty(self.$microsoftButton)) {
                    self.$microsoftButton = self._getMicrosoftButton();
                }
                self.$microsoftStopButton.replaceWith(self.$microsoftButton);
            },
            on_always: function() {
                self.$microsoftStopButton.prop('disabled', false);
            }
        });
    },

    _onArchiveEvent: function (event) {
        this._unselectEvent();
        this.trigger_up('archiveRecord', {id: parseInt(event.data.id, 10)});
    },
});

return {
    MicrosoftCalendarController,
    MicrosoftCalendarModel,
    MicrosoftCalendarRenderer,
};

});
