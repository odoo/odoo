import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarCommonPopover.prototype, {
    get isEventArchivable() {
        console.log(this.props.record.isInUserCalendars)
        return super.isEventArchivable || (
            (this.isCurrentUserOrganizer || this.props.record.isInUserCalendars) && this.props.record.rawRecord.google_id
        );
    },
});
