/** @odoo-module */

import { gridView } from "@web_grid/views/grid_view";
import { TimesheetGridController } from "./timesheet_grid_controller";
import { TimesheetGridModel } from "./timesheet_grid_model";
import { TimesheetGridRenderer } from "./timesheet_grid_renderer";
import { registry } from "@web/core/registry";
import { TimesheetGridSearchModel } from "./timesheet_grid_search_model";


export const timesheetGridView = {
    ...gridView,
    Controller: TimesheetGridController,
    Model: TimesheetGridModel,
    Renderer: TimesheetGridRenderer,
    SearchModel: TimesheetGridSearchModel,
};

registry.category("views").add('timesheet_grid', timesheetGridView);
