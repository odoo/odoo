/** @odoo-module */

import { registry } from "@web/core/registry";
import { TimesheetTimerListController } from "./timesheet_timer_list_controller";
import { TimesheetTimerListRenderer } from "./timesheet_timer_list_renderer";
import { listView } from "@web/views/list/list_view";

export const timesheetTimerListView = {
    ...listView,
    Controller: TimesheetTimerListController,
    Renderer: TimesheetTimerListRenderer,
};

registry.category("views").add("timesheet_timer_list", timesheetTimerListView);
