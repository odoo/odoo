import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { ProjectTaskCalendarController } from "./project_task_calendar_controller";
import { ProjectTaskCalendarModel } from "./project_task_calendar_model";
import { ProjectTaskCalendarRenderer } from "./project_task_calendar_renderer";
import { ProjectTaskControlPanel } from "../project_task_control_panel/project_task_control_panel";

export const projectTaskCalendarView = {
    ...calendarView,
    ControlPanel: ProjectTaskControlPanel,
    Controller: ProjectTaskCalendarController,
    Model: ProjectTaskCalendarModel,
    Renderer: ProjectTaskCalendarRenderer,
};
registry.category("views").add("project_task_calendar", projectTaskCalendarView);
