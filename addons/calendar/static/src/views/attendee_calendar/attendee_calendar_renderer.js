import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { AttendeeCalendarYearRenderer } from "@calendar/views/attendee_calendar/year/attendee_calendar_year_renderer";

export class AttendeeCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: AttendeeCalendarCommonRenderer,
        week: AttendeeCalendarCommonRenderer,
        month: AttendeeCalendarCommonRenderer,
        year: AttendeeCalendarYearRenderer,
    };
}
