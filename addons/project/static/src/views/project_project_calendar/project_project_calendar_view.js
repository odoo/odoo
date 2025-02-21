import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { ProjectProjectCalendarController } from "./project_project_calendar_controller";
import { ProjectCalendarRenderer } from "./project_project_calendar_renderer";

const viewRegistry = registry.category("views");

const projectProjectCalendarView = {
    ...calendarView,
    Controller: ProjectProjectCalendarController,
    Renderer: ProjectCalendarRenderer,
};

viewRegistry.add("project_project_calendar", projectProjectCalendarView);
