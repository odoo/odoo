import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { TimesheetListRenderer } from "./timesheet_list_renderer";

export const timesheetListView = {
    ...listView,
    Renderer : TimesheetListRenderer
}
registry.category("views").add("timesheet_list_view",timesheetListView)
