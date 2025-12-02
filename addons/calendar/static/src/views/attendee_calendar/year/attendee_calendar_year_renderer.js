import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";
import { AttendeeCalendarYearPopover } from "@calendar/views/attendee_calendar/year/attendee_calendar_year_popover";

export class AttendeeCalendarYearRenderer extends CalendarYearRenderer {
    static components = {
        ...CalendarYearRenderer.components,
        Popover: AttendeeCalendarYearPopover,
    };
}
