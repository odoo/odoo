/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";

import { TimesheetValidationKanbanController } from "./timesheet_validation_kanban_controller";

export const timesheetValidationKanbanView = {
    ...kanbanView,
    Controller: TimesheetValidationKanbanController,
    buttonTemplate: "timesheet_grid.TimesheetValidationKanbanView.Buttons",
};

registry.category("views").add("timesheet_validation_kanban", timesheetValidationKanbanView);
