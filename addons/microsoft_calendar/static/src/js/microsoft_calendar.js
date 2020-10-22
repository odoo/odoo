odoo.define('microsoft_calendar.CalendarView', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
const CalendarRenderer = require('calendar.CalendarRenderer');
const CalendarController = require('calendar.CalendarController');
const CalendarModel = require('calendar.CalendarModel');

var _t = core._t;

const {
    Component,
    hooks: {
        useState,
    },
} = owl;

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
            if (result.status === "need_config_from_admin" || result.status === "need_auth") {
                self.microsoft_is_sync = false;
            } else if (result.status === "no_new_event_from_microsoft" || result.status === "need_refresh") {
                self.microsoft_is_sync = true;
            }
            return result
        });
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
            }
        }).then(event.data.on_always, event.data.on_always);
    }
});

class MicrosoftCalendarButton extends Component {
    constructor() {
        super(...arguments);

        this.state = useState({
            disabled: false,
        });
    }
    /**
     * Requests to sync the calendar with Microsoft Calendar
     *
     * @private
     */
    _onSyncMicrosoftCalendar() {
        this.state.disabled = true;
        this.trigger('syncMicrosoftCalendar', {
            on_always: () => {
                this.state.disabled = false;
            },
        });
    }
}
MicrosoftCalendarButton.template = 'microsoft_calendar.CalendarButton';

CalendarRenderer.components.MicrosoftCalendarButton = MicrosoftCalendarButton;

return {
    MicrosoftCalendarController,
    MicrosoftCalendarModel,
    MicrosoftCalendarRenderer: CalendarRenderer,
};

});
