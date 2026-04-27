/** @odoo-module **/

import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { PlanningCalendarModel } from "./planning_calendar_model";
import { PlanningCalendarController } from "./planning_calendar_controller";
import { PlanningCalendarRenderer } from "./planning_calendar_renderer";
import { PlanningSearchModel } from "../planning_search_model";

export const planningCalendarView = {
    ...calendarView,
    SearchModel: PlanningSearchModel,
    Model: PlanningCalendarModel,
    Controller: PlanningCalendarController,
    Renderer: PlanningCalendarRenderer,
    buttonTemplate: "planning.PlanningCalendarController.controlButtons",
};
registry.category("views").add("planning_calendar", planningCalendarView);
