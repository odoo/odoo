import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { ActivityCalendarCommonPopover } from "./activity_calendar_common_popover";

export class ActivityCalendarCommonRender extends CalendarCommonRenderer {
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: ActivityCalendarCommonPopover,
    };
}
