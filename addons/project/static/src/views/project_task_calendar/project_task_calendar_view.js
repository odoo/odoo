/** @odoo-module **/

import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { ProjectControlPanel } from "@project/components/project_control_panel/project_control_panel";
import { ProjectTaskCalendarController } from "./project_task_calendar_controller";
import { ProjectTaskCalendarModel } from "./project_task_calendar_model";

export const projectTaskCalendarView = {
    ...calendarView,
    Controller: ProjectTaskCalendarController,
    ControlPanel: ProjectControlPanel,
    Model: ProjectTaskCalendarModel,
};
registry.category("views").add("project_task_calendar", projectTaskCalendarView);
