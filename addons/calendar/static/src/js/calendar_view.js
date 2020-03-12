odoo.define('calendar.CalendarView', function (require) {
    "use strict";

    const CalendarPopover = require('web.CalendarPopover');
    const CalendarRenderer = require('web.CalendarRenderer');
    const CalendarView = require('web.CalendarView');
    const viewRegistry = require('web.view_registry');

    class AttendeeCalendarPopover extends CalendarPopover {
        /**
         * @constructor
         */
        constructor(parent, props) {
            super(...arguments);
            // Show status dropdown if user is in attendees list
            this.showStatusDropdown = _.contains(this.event.record.partner_ids, this.env.session.partner_id);
            if (this.showStatusDropdown) {
                this.statusColors = {accepted: 'text-success', declined: 'text-danger', tentative: 'text-muted', needsAction: 'text-dark'};
                this.statusInfo = {};
                (this.fields.attendee_status.selection).forEach((selection) => {
                    this.statusInfo[selection[0]] = {text: selection[1], color: this.statusColors[selection[0]]};
                });
                this.selectedStatusInfo = this.statusInfo[this.event.record.attendee_status];
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickAttendeeStatus(ev) {
            ev.preventDefault();
            const selectedStatus = $(ev.currentTarget).attr('data-action');
            this.env.services.rpc({
                model: 'calendar.event',
                method: 'change_attendee_status',
                args: [this.event.id, selectedStatus],
            }).then(() => {
                this.event.record.attendee_status = selectedStatus;  // FIXEME: Maybe we have to reload view
                this.el.querySelectorAll('.o-calendar-attendee-status-text').forEach(node => {
                    node.innerHTML = this.statusInfo[selectedStatus].text;
                });
                this.el.querySelectorAll('.o-calendar-attendee-status-icon').forEach(node => {
                    for (const key in this.statusColors) {
                        node.classList.remove(this.statusColors[key]);
                    }
                    node.classList.add(this.statusInfo[selectedStatus].color);
                });
            });
        }
    }

    AttendeeCalendarPopover.template = "Calendar.attendee.status.popover";

    const AttendeeCalendarRenderer = CalendarRenderer;
    AttendeeCalendarRenderer.prototype.config = Object.assign(CalendarRenderer.prototype.config, {
        CalendarPopover: AttendeeCalendarPopover
    });

    const AttendeeCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Renderer: AttendeeCalendarRenderer,
        }),
    });

    viewRegistry.add('attendee_calendar', AttendeeCalendarView);

});
