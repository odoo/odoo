/** @odoo-module alias=calendar.CalendarModel **/

    import Model from 'web.CalendarModel';

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
                const currentPartnerId = this.getSession().partner_id;
                eventsData.forEach(event => {
                    const attendees = event.record.partner_ids && event.record.partner_ids.length ? event.record.partner_ids : [event.record.partner_id[0]];
                    // Get the list of partner_id corresponding to active filters present in the current event
                    const attendees_filtered = attendeeFilters.filters.reduce((acc, filter) => {
                        if (filter.active && attendees.includes(filter.value)) {
                            acc.push(filter.value);
                        }
                        return acc;
                    }, []);

                    // Create Event data for each attendee found
                    attendees_filtered.forEach(attendee => {
                        let e = $.extend(true, {}, event);
                        e.attendee_id = attendee;
                        const attendee_info = self.attendees.find(a => a.id === attendee && a.event_id === e.record.id);
                        if (attendee_info) {
                            e.record.attendee_status = attendee_info.status;
                            e.record.is_alone = attendee_info.is_alone;
                            // check if this event data corresponds to the current partner
                            e.record.is_current_partner = currentPartnerId === attendee_info.id;
                        }
                        eventsDataByAttendee.push(e);
                    });
                });
            } else {
                eventsData.forEach(event => {
                    const attendee_info = self.attendees.find(a => a.id === self.getSession().partner_id && a.event_id === event.record.id);
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

    /**
     * Set the event color according to the filters values.
     * When Everybodies'events are displayed, the color are set according to the first attendee_id to decrease confusion.
     * Else, the event color are defined according to the existing filters colors.
     * @private
     * @param {any} element
     * @param {any} events
     * @returns {Promise}
     */
    _loadColors: function (element, events) {
        if (this.fieldColor) {
            const fieldName = this.fieldColor;
            for (const event of events) {
                // list of partners in case of calendar event
                const value = event.record[fieldName];
                const colorRecord = value[0];
                const filter = this.loadParams.filters[fieldName];
                const colorFilter = filter && filter.filters.map(f => f.value) || [colorRecord];
                const everyoneFilter = filter && (filter.filters.find(f => f.value === "all") || {}).active || false;
                let colorValue;
                if (!everyoneFilter) {
                    colorValue = event.attendee_id;
                } else {
                    const partner_id = this.getSession().partner_id
                    colorValue = value.includes(partner_id) ? partner_id : colorRecord;
                }
                event.color_index = this._getColorIndex(colorFilter, colorValue);
            }
            this.model_color = this.fields[fieldName].relation || element.model;

        }
        return Promise.resolve();
    },

    });

    export default CalendarModel;
