odoo.define('calendar.CalendarModel', function (require) {
    "use strict";

    const Model = require('web.CalendarModel');

    const CalendarModel = Model.extend({

        /**
         * @override
         * Transform fullcalendar event object to odoo Data object
         */
        calendarEventToRecord(event) {
            const data = this._super(event);
            return _.extend({}, data, {
                'recurrence_update': event.recurrenceUpdate,
            });
        },
        async _getCalendarEventData(events) {
            const calendarEventData = await this._super(...arguments);
            const calendarEventByAttendeeData = await this._calendarEventByAttendee(calendarEventData);
            return calendarEventByAttendeeData;
        },
        /**
         * Split the events to display an event for each attendee with the correct status.
         * If the all filter is activated, we don't display an event for each attendee and keep
         * the previous behavior to display a single event.
         * 
         */
        async _calendarEventByAttendee(eventsData) {
            const self = this;
            let eventsDataByAttendee = [];
            const attendeeFilters = self.loadParams.filters.partner_ids;
            const everyoneFilter = attendeeFilters && (attendeeFilters.filters.find(f => f.value === "all") || {}).active || false;
            const attendeeIDs = attendeeFilters && _.filter(attendeeFilters.filters.map(partner => partner.value !== 'all' ? partner.value : false), id => id !== false);
            const eventIDs = eventsData.map(event => event.id);
            // Fetch the attendees' info from the partners selected in the filter to display the events
            this.attendees = await self._rpc({
                model: 'res.partner',
                method: 'get_attendee_detail',
                args: [attendeeIDs, eventIDs],
            });
            if (!everyoneFilter) {
                eventsData.forEach(event => {
                    (event.record.partner_ids || []).forEach(attendee => {
                        if (attendeeFilters.filters.find(f => f.active && f.value == attendee)) {
                            let e = $.extend(true, {}, event);
                            e.attendee_id = attendee;
                            const attendee_info = self.attendees.find(a => a.id == attendee && a.event_id == e.record.id);
                            if (attendee_info) {
                                e.record.attendee_status = attendee_info.status;
                                e.record.is_alone = attendee_info.is_alone;
                            }
                            eventsDataByAttendee.push(e);
                        }
                    });
                });
            } else {
                eventsData.forEach(event => {
                    const attendee_info = self.attendees.find(a => a.id == self.getSession().partner_id && a.event_id == event.record.id);
                    if (attendee_info) {
                        event.record.is_alone = attendee_info.is_alone;
                    }
                });
            }
            return eventsDataByAttendee.length ? eventsDataByAttendee : eventsData;
        },

        /**
         * Decline an event for the actual attendee
         * @param {Integer} eventId
         */
        declineEvent: function (event) {
            return this._rpc({
                model: 'calendar.attendee',
                method: 'do_decline',
                args: [this.attendees.find(attendee => attendee.event_id === event.id && attendee.id === this.getSession().partner_id).attendee_id],
            });
        },
    });

    return CalendarModel;
});
