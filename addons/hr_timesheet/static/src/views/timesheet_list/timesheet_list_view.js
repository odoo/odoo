/** @odoo-module */

import { registry } from "@web/core/registry";
import { TimesheetListController } from "./timesheet_list_controller";
import { listView } from "@web/views/list/list_view";

export const timesheetListView = {
    ...listView,
    Controller: TimesheetListController,
};

registry.category("views").add("timesheet_list", timesheetListView);
