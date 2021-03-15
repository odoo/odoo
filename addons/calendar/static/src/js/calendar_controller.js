odoo.define('calendar.CalendarController', function (require) {
    "use strict";

    const Controller = require('web.CalendarController');
    const Dialog = require('web.Dialog');
    const { qweb, _t } = require('web.core');
    const core = require('web.core');
    const QWeb = core.qweb;

    const CalendarController = Controller.extend({

    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        const $addButton =  $(QWeb.render('Calendar.calendar_add_buttons'));
        this.$buttons.prepend($addButton)
        const self = this;
        // When clicking on "Add", create a new record in form view
        this.$buttons.on('click', 'button.o-calendar-button-new', () => {
            return self.do_action('calendar.action_calendar_event_notify', {
                additional_context: self.context,
            });
        });
    },

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
         * If the event comes from the organizer we delete the event, else we the event is decline for the attendee
         * @override 
         */
        _onDeleteRecord: function (ev) {
            const event = _.find(this.model.data.data, e => e.id === ev.data.id && e.attendee_id === ev.data.event.attendee_id);
            if (this.getSession().partner_id === event.attendee_id && this.getSession().partner_id === event.record.partner_id[0]) {
                this._super(...arguments);
            } else {
                var self = this;
                this.model.declineEvent(event).then(function () {
                    self.reload();
                });
            }
        },

        /**
         * @override
         * @private
         * @param {OdooEvent} event
         */
        async _onDropRecord(event) {
            const _super = this._super; // reference to this._super is lost after async call
            await this._dropdUpdateRecord(event);
            _super.apply(this, arguments);
        },

        /**
         * @override
         * @private
         * @param {OdooEvent} event
         */
        async _onUpdateRecord(event) {
            const _super = this._super;  // reference to this._super is lost after async call
            await this._dropdUpdateRecord(event);
            _super.apply(this, arguments);
        },

        async _dropdUpdateRecord(event) {
            if (event.data.record.recurrency) {
                const recurrenceUpdate = await this._askRecurrenceUpdatePolicy();
                event.data = _.extend({}, event.data, {
                    'recurrenceUpdate': recurrenceUpdate,
                });
            }
        }

    });

    return CalendarController;

});
