/** @odoo-module **/

import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

import { TimesheetValidationPivotRenderer } from "./timesheet_validation_pivot_renderer";

export const TimesheetValidationPivotView = {
    ...pivotView,
    Renderer: TimesheetValidationPivotRenderer,
    buttonTemplate: "timesheet_grid.TimesheetValidationPivotView.Buttons",
};

registry.category("views").add("timesheet_validation_pivot_view", TimesheetValidationPivotView);
