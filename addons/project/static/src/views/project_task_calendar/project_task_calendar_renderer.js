import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { ProjectTaskCalendarCommonRenderer } from "./project_task_calendar_common/project_task_calendar_common_renderer";
import { ProjectTaskCalendarYearRenderer } from "./project_task_calendar_year/project_task_calendar_year_renderer";

export class ProjectTaskCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: ProjectTaskCalendarCommonRenderer,
        week: ProjectTaskCalendarCommonRenderer,
        month: ProjectTaskCalendarCommonRenderer,
        year: ProjectTaskCalendarYearRenderer,
    };
}
