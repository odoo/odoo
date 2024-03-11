/** @odoo-module **/

import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarCommonPopover.prototype, "google_calendar_google_calendar_common_popover", {
    get isEventArchivable() {
        return this._super() || (this.isCurrentUserOrganizer && this.props.record.rawRecord.google_id);
    },
});
