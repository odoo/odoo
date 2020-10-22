odoo.define('calendar.CalendarController', function (require) {
    "use strict";

    const Controller = require('web.CalendarController');
    const Dialog = require('web.Dialog');
    const { qweb, _t } = require('web.core');

    const CalendarController = Controller.extend({
        custom_events: Object.assign({}, Controller.prototype.custom_events, {
            attendee_status_changed: '_onAttendeeStatusChanged',
        }),

        _askRecurrenceUpdatePolicy() {
            return new Promise((resolve, reject) => {
                new Dialog(this, {
                    title: _t('Edit Recurrent event'),
                    size: 'small',
                    $content: $(qweb.render('calendar.RecurrentEventUpdate')),
                    buttons: [{
                        text: _t('Confirm'),
                        classes: 'btn-primary',
                        close: true,
                        click: function () {
                            resolve(this.$('input:checked').val());
                        },
                    }],
                }).open();
            });
        },

        /**
         * @private
         * @param {OdooEvent} ev
         */
        async _onAttendeeStatusChanged(ev) {
            await this._rpc({
                model: 'calendar.event',
                method: 'change_attendee_status',
                args: [
                    ev.data.eventId,
                    ev.data.status,
                ],
            });
            this.reload();
        },
        // TODO factorize duplicated code
        /**
         * @override
         * @private
         * @param {OdooEvent} event
         */
        async _onDropRecord(event) {
            const _super = this._super; // reference to this._super is lost after async call
            if (event.data.record.recurrency) {
                const recurrenceUpdate = await this._askRecurrenceUpdatePolicy();
                event.data = _.extend({}, event.data, {
                    'recurrenceUpdate': recurrenceUpdate,
                });
            }
            _super.apply(this, arguments);
        },

        /**
         * @override
         * @private
         * @param {OdooEvent} event
         */
        async _onUpdateRecord(event) {
            const _super = this._super;  // reference to this._super is lost after async call
            if (event.data.record.recurrency) {
                const recurrenceUpdate = await this._askRecurrenceUpdatePolicy();
                event.data = _.extend({}, event.data, {
                    'recurrenceUpdate': recurrenceUpdate,
                });
            }
            _super.apply(this, arguments);
        },

    });

    return CalendarController;

});
