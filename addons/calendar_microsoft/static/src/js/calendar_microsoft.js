odoo.define('calendar_microsoft.CalendarView', function (require) {
    "use strict";

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    const CalendarRenderer = require('@calendar/js/calendar_renderer')[Symbol.for("default")].AttendeeCalendarRenderer;
    const CalendarController = require('@calendar/js/calendar_controller')[Symbol.for("default")];
    const CalendarModel = require('@calendar/js/calendar_model')[Symbol.for("default")];

    var _t = core._t;

    const MicrosoftCalendarModel = CalendarModel.include({

        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.microsoft_sync_enabled = true;
        },

        /**
         * @override
         */
        __get: function () {
            var result = this._super.apply(this, arguments);
            result.microsoft_sync_enabled = this.microsoft_sync_enabled;
            return result;
        },

        /**
         * @override
         * Note: used to update the status of the microsoft calendar sync.
         */
        async _loadCalendar() {
            var self = this;
            const _super = this._super.bind(this);
            try {
                await this.get_sync_status().then(function (res) {
                    self.microsoft_sync_enabled = res.isEnabled;
                });
            }
            catch (error) {
                this.microsoft_sync_enabled = false;
            }
            return _super(...arguments);
        },

        get_sync_status: function () {
            return this._rpc({
                route: '/calendar_microsoft/sync_status',
                params: {}
            }, { shadow: false });
        },
    });

    const MicrosoftCalendarController = CalendarController.include({
        custom_events: _.extend({}, CalendarController.prototype.custom_events, {
            enableMicrosoftCalendarSync: '_onEnableMicrosoftCalendarSync',
            disableMicrosoftCalendarSync: '_onDisableMicrosoftCalendarSync',
        }),

        /**
         * Enable Microsoft Calendar sync.
         * May require an action from the user if credentials are not correctly configured.
         *
         * @private
         * @returns {OdooEvent} event
         */
        _onEnableMicrosoftCalendarSync: function (event) {
            var self = this;
            return this._enableSync()
                .then(function (res) {
                    self._confirmSyncIsEnabled(res, event);
                    return event.data.on_always();
                })
        },

        /**
         * Disable Microsoft Calendar sync.
         *
         * @private
         * @returns {OdooEvent} event
         */
        _onDisableMicrosoftCalendarSync: function (event) {
            var self = this;
            Dialog.confirm(
                this,
                _t("You are about to stop the synchronization of your calendar with Outlook. Are you sure you want to continue?"),
                {
                    confirm_callback: function () {
                        return self._disableSync()
                            .then(function () {
                                self._confirmSyncIsDisabled();
                                return event.data.on_confirm();
                            });
                    },
                    title: _t('Confirmation'),
                });
            return event.data.on_always();
        },

        /**
         * RPC call to the Odoo instance to enable Microsoft Calendar sync.
         */
        _enableSync: function () {
            return this._rpc({
                route: '/calendar_microsoft/enable_sync',
                params: {
                    from_url: window.location.href,
                }
            }, { shadow: false });
        },

        /**
         * RPC call to the Odoo instance to disable Microsoft Calendar sync.
         */
        _disableSync: function () {
            return this._rpc({
                route: '/calendar_microsoft/disable_sync',
                params: {}
            }, { shadow: false });
        },

        /**
         * Confirm that the Microsoft Calendar sync has been correctly enabled.
         * Note: return a confirming function (closure) which encapsulates the `event` 
         * and it may be used in the confirming process. 
         */
        _confirmSyncIsEnabled: function (res, event) {
            if (res.status === "need_auth") {
                Dialog.alert(
                    this,
                    _t("You will be redirected to Outlook to authorize the access to your calendar."),
                    {
                        confirm_callback: function () {
                            framework.redirect(res.url);
                        },
                        title: _t('Redirection'),
                    });
            }
            else if (res.status === "need_config_from_admin") {
                if (!_.isUndefined(res.action) && parseInt(res.action)) {
                    Dialog.confirm(
                        this,
                        _t("The Outlook Synchronization needs to be configured before you can use it, do you want to do it now?"),
                        {
                            confirm_callback: function () {
                                this.do_action(res.action);
                            },
                            title: _t('Configuration'),
                        });
                } else {
                    Dialog.alert(
                        this,
                        _t("An administrator needs to configure Outlook Synchronization before you can use it!"),
                        {
                            title: _t('Configuration'),
                        });
                }
            }
            else {
                this.model.microsoft_sync_enabled = true;
                return event.data.on_refresh();
            }
        },

        /**
         * Confirm that the Microsoft Calendar sync has been correctly enabled.
         */
        _confirmSyncIsDisabled: function () {
            this.displayNotification({
                title: _t("Success"),
                message: _t("The synchronization with Outlook calendar was successfully stopped."),
                type: 'success',
            });
            this.model.microsoft_sync_enabled = false;
        }
    });

    const MicrosoftCalendarRenderer = CalendarRenderer.include({
        events: _.extend({}, CalendarRenderer.prototype.events, {
            'click .o_microsoft_sync_pending': '_onEnableMicrosoftCalendarSync',
            'click .o_microsoft_sync_button_configured': '_onDisableMicrosoftCalendarSync',
        }),

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _initMicrosoftPillButton: function () {
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
            if (this.state.microsoft_sync_enabled) {
                self.$microsoftButton.hide();
                self.$microsoftStopButton.show();
                this._initMicrosoftPillButton();
            } else {
                self.$microsoftButton.show();
                self.$microsoftStopButton.hide();
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
        _onEnableMicrosoftCalendarSync: function () {
            var self = this;
            this.$microsoftButton.prop('disabled', true);
            this.trigger_up('enableMicrosoftCalendarSync', {
                on_refresh: function () {
                    self.$microsoftStopButton.show();
                    self.$microsoftButton.hide();
                    self._initMicrosoftPillButton();
                },
                on_always: function () {
                    self.$microsoftButton.prop('disabled', false);
                },
            });
        },

        _onDisableMicrosoftCalendarSync: function () {
            var self = this;
            this.$microsoftStopButton.prop('disabled', true);
            this.trigger_up('disableMicrosoftCalendarSync', {
                on_confirm: function () {
                    self.$microsoftStopButton.hide();
                    self.$microsoftButton.show();
                },
                on_always: function () {
                    self.$microsoftStopButton.prop('disabled', false);
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
