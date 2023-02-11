odoo.define('microsoft_calendar.MicrosoftCalendarPopover', function(require) {
    "use strict";

    const CalendarPopover = require('@calendar/js/calendar_renderer')[Symbol.for("default")].AttendeeCalendarPopover;

    const MicrosoftCalendarPopover = CalendarPopover.include({
        events: _.extend({}, CalendarPopover.prototype.events, {
            'click .o_cw_popover_archive_m': '_onClickPopoverArchive',
        }),

        /**
         * We only want one 'Archive' button in the popover
         * so if Google Sync is active, it takes precedence
         * over this popover.
         */
        isMEventSyncedAndArchivable() {
            if (this.event.extendedProps.record.google_id === undefined) {
                return this.isCurrentPartnerOrganizer() && this.event.extendedProps.record.microsoft_id;
            }
            return this.isCurrentPartnerOrganizer() && !this.event.extendedProps.record.google_id && this.event.extendedProps.record.microsoft_id
        },

        isEventDeletable() {
            return !this.isMEventSyncedAndArchivable() && this._super();
        },

        _onClickPopoverArchive: function (ev) {
            ev.preventDefault();
            this.trigger_up('archive_event', {id: this.event.id});
        },
    });

    return MicrosoftCalendarPopover;
});
