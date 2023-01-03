/** @odoo-module **/

import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarCommonPopover.prototype, "microsoft_calendar_microsoft_calendar_common_popover", {
    get isEventArchivable() {
        return this._super() || (this.isCurrentUserOrganizer && this.props.record.rawRecord.microsoft_id);
    },
});
