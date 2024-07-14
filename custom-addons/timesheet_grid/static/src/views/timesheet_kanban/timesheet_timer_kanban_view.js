/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { TimesheetTimerKanbanController } from "./timesheet_timer_kanban_controller";
import { TimesheetTimerKanbanRenderer } from "./timesheet_timer_kanban_renderer";

export const timesheetTimerKanbanView = {
    ...kanbanView,
    Controller: TimesheetTimerKanbanController,
    Renderer: TimesheetTimerKanbanRenderer,
};

registry.category("views").add("timesheet_timer_kanban", timesheetTimerKanbanView);
