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

        Promise.all([
            self._rpc({model: self.modelName, method: 'check_access_rule', args: [parseInt(this.event.id), "write", false]}),
            self._rpc({model: self.modelName, method: 'check_access_rule', args: [parseInt(this.event.id), "unlink", false]}),
        ]).then(function (result) {
            self.editable = result[0]
            self.deletable = result[1]
        });
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
        return this.deletable;
    },
    /**
     * @override
     * @return {boolean}
     */
    isEventEditable() {
        return this.editable;
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
