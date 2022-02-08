odoo.define('google_calendar.GoogleCalendarPopover', function(require) {
    "use strict";

    const CalendarPopover = require('@calendar/js/calendar_renderer')[Symbol.for("default")].AttendeeCalendarPopover;

    const GoogleCalendarPopover = CalendarPopover.include({
        events: _.extend({}, CalendarPopover.prototype.events, {
            'click .o_cw_popover_archive_g': '_onClickPopoverGArchive',
        }),

        isGEventSyncedAndArchivable() {
            return this.isCurrentPartnerOrganizer() && this.event.extendedProps.record.google_id;
        },

        isEventDeletable() {
            return !this.isGEventSyncedAndArchivable() && this._super();
        },

        _onClickPopoverGArchive: function (ev) {
            ev.preventDefault();
            this.trigger_up('archive_event', {id: this.event.id});
        },
    });

    return GoogleCalendarPopover;
});
