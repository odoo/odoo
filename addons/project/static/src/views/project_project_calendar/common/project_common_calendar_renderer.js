import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { ProjectCalendarCommonPopover } from "./project_common_calendar_popover";

export class ProjectCalendarCommonRenderer extends CalendarCommonRenderer {
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: ProjectCalendarCommonPopover,
    };
}
