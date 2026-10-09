import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";

export class AttendanceCalendarCommonRenderer extends CalendarCommonRenderer {
    /**
     * @override
     * Open the attendance directly instead of the popover.
     */
    onClick(info) {
        return this.onDblClick(info);
    }
}
