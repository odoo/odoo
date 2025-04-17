import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";

export class EventSlotCalendarCommonRenderer extends CalendarCommonRenderer {
    // Display end time and hide title on the full calendar library event.
    static eventTemplate = "event.EventSlotCalendarCommonRenderer.event";
}

export class EventSlotCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: EventSlotCalendarCommonRenderer,
        week: EventSlotCalendarCommonRenderer,
        month: EventSlotCalendarCommonRenderer,
        year: CalendarYearRenderer,
    };
}
