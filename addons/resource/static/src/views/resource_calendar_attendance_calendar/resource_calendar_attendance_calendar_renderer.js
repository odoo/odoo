import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { ResourceCalendarAttendanceCalendarCommonRenderer } from "./resource_calendar_attendance_calendar_common_renderer";

export class ResourceCalendarAttendanceCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        week: ResourceCalendarAttendanceCalendarCommonRenderer,
        month: ResourceCalendarAttendanceCalendarCommonRenderer,
    };
}
