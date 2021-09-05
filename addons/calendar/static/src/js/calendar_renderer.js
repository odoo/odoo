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
    isCurrentPartnerOrganizer() {
        return this.event.extendedProps.record.partner_id[0] === session.partner_id;
    },
    /**
     * @return {boolean}
     */
    isCurrentPartnerAttendee() {
        return this.event.extendedProps.record.partner_ids.includes(session.partner_id) && this.event.extendedProps.attendee_id === session.partner_id;
    },
    /**
     * @override
     * @return {boolean}
     */
    isEventDeletable() {
        return this._super() && this.isCurrentPartnerAttendee();
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
            self.$el.parent().hide();
            self.trigger_up('render_event');
        });
    },
});


const AttendeeCalendarRenderer = CalendarRenderer.extend({
	config: _.extend({}, CalendarRenderer.prototype.config, {
        CalendarPopover: AttendeeCalendarPopover,
        eventTemplate: 'Calendar.calendar-box',
    }),
    /**
     * Add the attendee-id attribute in order to distinct the events when there are
     * several attendees in the event.
     * @override
     */
    _addEventAttributes: function (element, event) {
        this._super(...arguments);
        element.attr('data-attendee-id', event.extendedProps.attendee_id);
    },
    /**
     * If an attendee_id has been set on the event, we check also the attendee-id attribute
     * to select the good event on which the CSS class will be applied.
     * @override
     */
    _computeEventSelector: function (info) {
        let selector = this._super(...arguments);
        if (info.event.extendedProps.attendee_id) {
            selector += `[data-attendee-id=${info.event.extendedProps.attendee_id}]`;
        }
        return selector;
    },
});

return {
    AttendeeCalendarRenderer: AttendeeCalendarRenderer,
    AttendeeCalendarPopover: AttendeeCalendarPopover,
};

});
