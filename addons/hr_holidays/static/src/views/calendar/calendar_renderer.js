import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";

import { TimeOffCalendarCommonRenderer } from "./common/calendar_common_renderer";
import { TimeOffCalendarYearRenderer } from "./year/calendar_year_renderer";

export class TimeOffCalendarRenderer extends CalendarRenderer {
    static template = "hr_holidays.CalendarRenderer";
    static components = {
        ...TimeOffCalendarRenderer.components,
        day: TimeOffCalendarCommonRenderer,
        week: TimeOffCalendarCommonRenderer,
        month: TimeOffCalendarCommonRenderer,
        year: TimeOffCalendarYearRenderer,
    };
}
