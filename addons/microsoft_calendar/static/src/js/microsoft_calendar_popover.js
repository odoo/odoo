odoo.define('microsoft_calendar.MicrosoftCalendarPopover', function(require) {
    "use strict";

    const CalendarPopover = require('web.CalendarPopover');

    const MicrosoftCalendarPopover = CalendarPopover.include({
        events: _.extend({}, CalendarPopover.prototype.events, {
            'click .o_cw_popover_archive_m': '_onClickPopoverArchive',
        }),

        /**
         * We only want one 'Archive' button in the popover
         * so if Google Sync is also active, it takes precedence
         * over this popvoer.
         */
        isMEventSyncedAndArchivable() {
            if (this.event.extendedProps.record.google_id === undefined) {
                return this.event.extendedProps.record.microsoft_id;
            }
            return !this.event.extendedProps.record.google_id && this.event.extendedProps.record.microsoft_id
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
