import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { ActivityCalendarYearRenderer } from "./calendar_year/activity_calendar_year_renderer";

export class ActivityCalendarRender extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        year: ActivityCalendarYearRenderer,
    };
}
