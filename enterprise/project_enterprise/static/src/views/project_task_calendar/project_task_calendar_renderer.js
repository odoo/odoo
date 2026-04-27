import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { ProjectTaskCalendarCommonRenderer } from "./common/project_task_calendar_common_renderer";

export class ProjectTaskCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: ProjectTaskCalendarCommonRenderer,
        week: ProjectTaskCalendarCommonRenderer,
        month: ProjectTaskCalendarCommonRenderer,
    };
}
