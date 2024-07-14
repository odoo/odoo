/** @odoo-module **/

import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

import { TimesheetValidationPivotRenderer } from "./timesheet_validation_pivot_controller";

export const TimesheetValidationPivotView = {
    ...pivotView,
    Renderer: TimesheetValidationPivotRenderer,
};

registry.category("views").add("timesheet_validation_pivot_view", TimesheetValidationPivotView);
