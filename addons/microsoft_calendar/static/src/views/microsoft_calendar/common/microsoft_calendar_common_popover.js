import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarCommonPopover.prototype, {
    get isEventArchivable() {
        return super.isEventArchivable || (this.isCurrentUserOrganizer && this.props.record.rawRecord.microsoft_id);
    },
});
