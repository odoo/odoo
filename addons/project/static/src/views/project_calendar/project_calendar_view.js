/** @odoo-module **/

import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { ProjectCalendarController } from "@project/views/project_calendar/project_calendar_controller";
import { ProjectControlPanel } from "@project/components/project_control_panel/project_control_panel";
import { ProjectCalendarModel } from "./project_calendar_model";

export const projectCalendarView = {
    ...calendarView,
    Controller: ProjectCalendarController,
    Model: ProjectCalendarModel,
    ControlPanel: ProjectControlPanel,
};
registry.category("views").add("project_calendar", projectCalendarView);
