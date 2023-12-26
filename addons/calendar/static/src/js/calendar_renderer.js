odoo.define('calendar.CalendarRenderer', function (require) {
"use strict";

const CalendarRenderer = require('web.CalendarRenderer');
const CalendarPopover = require('web.CalendarPopover');
const session = require('web.session');


const AttendeeCalendarPopover = CalendarPopover.extend({
    template: 'Calendar.attendee.status.popover',
    events: _.extend({}, CalendarPopover.prototype.events, {
        'click .o-calendar-attendee-status .dropdown-item': '_onClickAttendeeStatus'
    }),
    /**
     * @constructor
     */
    init: function () {
        var self = this;
        this._super.apply(this, arguments);
        // Show status dropdown if user is in attendees list
        if (this.isCurrentPartnerAttendee()) {
            this.statusColors = {accepted: 'text-success', declined: 'text-danger', tentative: 'text-muted', needsAction: 'text-dark'};
            this.statusInfo = {};
            _.each(this.fields.attendee_status.selection, function (selection) {
                self.statusInfo[selection[0]] = {text: selection[1], color: self.statusColors[selection[0]]};
            });
            this.selectedStatusInfo = this.statusInfo[this.event.extendedProps.record.attendee_status];
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {boolean}
     */
    isCurrentPartnerAttendee() {
        return this.event.extendedProps.record.partner_ids.includes(session.partner_id);
    },
    /**
     * @override
     * @return {boolean}
     */
    isEventDeletable() {
        return this._super() && (this._isEventPrivate() ? this.isCurrentPartnerAttendee() : true);
    },
    /**
     * @override
     * @return {boolean}
     */
    isEventDetailsVisible() {
        return this._isEventPrivate() ? this.isCurrentPartnerAttendee() : this._super();
    },
    /**
     * @override
     * @return {boolean}
     */
    isEventEditable() {
        return this._isEventPrivate() ? this.isCurrentPartnerAttendee() : this._super();
    },
     /**
     * @return {boolean}
     */
    displayAttendeeAnswerChoice() {
        // check if we are a partner and if we are the only attendee.
        // This avoid to display attendee anwser dropdown for single user attendees
        const isCurrentpartner = (currentValue) => currentValue === session.partner_id;
        const onlyAttendee = this.event.extendedProps.record.partner_ids.every(isCurrentpartner);
        return this.isCurrentPartnerAttendee() && ! onlyAttendee;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {boolean}
     */
    _isEventPrivate() {
        return this.event.extendedProps.record.privacy === 'private';
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAttendeeStatus: function (ev) {
        ev.preventDefault();
        var self = this;
        var selectedStatus = $(ev.currentTarget).attr('data-action');
        this._rpc({
            model: 'calendar.event',
            method: 'change_attendee_status',
            args: [parseInt(this.event.id), selectedStatus],
        }).then(function () {
            self.event.extendedProps.record.attendee_status = selectedStatus;  // FIXEME: Maybe we have to reload view
            self.$('.o-calendar-attendee-status-text').text(self.statusInfo[selectedStatus].text);
            self.$('.o-calendar-attendee-status-icon').removeClass(_.values(self.statusColors).join(' ')).addClass(self.statusInfo[selectedStatus].color);
        });
    },
});


const AttendeeCalendarRenderer = CalendarRenderer.extend({
	config: _.extend({}, CalendarRenderer.prototype.config, {
		CalendarPopover: AttendeeCalendarPopover,
	}),
});

return AttendeeCalendarRenderer

});
