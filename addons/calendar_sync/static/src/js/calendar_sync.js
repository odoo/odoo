odoo.define('calendar_sync.CalendarView', function (require) {
    "use strict";

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    const CalendarRenderer = require('@calendar/js/calendar_renderer')[Symbol.for("default")].AttendeeCalendarRenderer;
    const CalendarController = require('@calendar/js/calendar_controller')[Symbol.for("default")];
    const CalendarModel = require('@calendar/js/calendar_model')[Symbol.for("default")];
    const session = require('web.session');

    var _t = core._t;

    const CalendarSyncModel = CalendarModel.include({

        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.is_sync_in_progress = false;
        },

        /**
         * @override
         * @returns {Promise}
         */
        async _loadCalendar() {
            const _super = this._super.bind(this);

            // When the calendar synchronization takes some time, prevents retriggering the sync while navigating
            // the calendar.
            if (this.is_sync_in_progress) {
                return _super(...arguments);
            }

            try {
                await Promise.race([
                    new Promise(resolve => setTimeout(resolve, 1000)),
                    this._syncCalendar(true)
                ]);
            } catch (error) {
                if (error.event) {
                    error.event.preventDefault();
                }
                console.error("Could not synchronize calendars now.", error);
                this.is_sync_in_progress = false;
            }
            return _super(...arguments);
        },

        _syncCalendar(shadow = false) {
            this.is_sync_in_progress = true;
            return this._rpc({
                route: '/calendar_sync/sync_calendars',
                params: {
                    model: this.modelName,
                    fromurl: window.location.href,
                }
            }, { shadow }).then(result => result);
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

    const CalendarSyncController = CalendarController.include({
        custom_events: _.extend({}, CalendarController.prototype.custom_events, {
            archiveRecord: '_onArchiveRecord',
        }),

        _onArchiveRecord: async function (event) {
            const self = this;
            if (event.data.event.record.recurrency) {
                const recurrenceUpdate = await this._askRecurrenceUpdatePolicy();
                event.data = Object.assign({}, event.data, {
                    'recurrenceUpdate': recurrenceUpdate,
                });
                if (recurrenceUpdate === 'self_only') {
                    self.model.archiveRecords([event.data.id], self.modelName).then(function () {
                        self.reload();
                    });
                } else {
                    return this._rpc({
                        model: self.modelName,
                        method: 'action_mass_archive',
                        args: [[event.data.id], recurrenceUpdate],
                    }).then(function () {
                        self.reload();
                    });
                }
            } else {
                Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
                    confirm_callback: function () {
                        self.model.archiveRecords([event.data.id], self.modelName).then(function () {
                            self.reload();
                        });
                    }
                });
            }
        },
    });

    const CalendarSyncRenderer = CalendarRenderer.include({
        custom_events: _.extend({}, CalendarRenderer.prototype.custom_events, {
            archive_event: '_onArchiveEvent',
        }),

        _onArchiveEvent: function (event) {
            this._unselectEvent();
            this.trigger_up('archiveRecord', { id: parseInt(event.data.id, 10), event: event.target.event.extendedProps });
        },
    });

    return {
        CalendarSyncController,
        CalendarSyncModel,
        CalendarSyncRenderer,
    };

});
