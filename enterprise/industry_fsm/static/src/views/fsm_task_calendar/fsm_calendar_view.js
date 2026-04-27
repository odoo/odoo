/** @odoo-module **/

import { registry } from "@web/core/registry";
import { projectTaskCalendarView } from "@project/views/project_task_calendar/project_task_calendar_view";
import { FsmTaskCalendarModel } from "./fsm_calendar_model";

export const fsmTaskCalendarView = {
    ...projectTaskCalendarView,
    Model: FsmTaskCalendarModel,
};

registry.category("views").add("fsm_task_calendar", fsmTaskCalendarView);
