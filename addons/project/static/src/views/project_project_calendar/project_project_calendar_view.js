/** @odoo-module **/

import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { ProjectProjectCalendarController } from "./project_project_calendar_controller";

const viewRegistry = registry.category("views");

const projectProjectCalendarView = {
    ...calendarView,
    Controller: ProjectProjectCalendarController,
};

viewRegistry.add("project_project_calendar", projectProjectCalendarView);
