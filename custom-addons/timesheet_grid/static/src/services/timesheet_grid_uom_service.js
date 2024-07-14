/** @odoo-module */

import { registry } from "@web/core/registry";
import { GridTimesheetUOM } from "../components/grid_timesheet_uom/grid_timesheet_uom";

export const timesheetGridUOMService = {
    dependencies: ["timesheet_uom"],
    start(env, { timesheet_uom }) {
        let formatter = timesheet_uom.formatter;
        const gridRegistry = registry.category("grid_components");
        if (timesheet_uom.timesheetWidget === "float_time") {
            formatter = gridRegistry.get("float_time", { formatter }).formatter;
        }
        gridRegistry.add("timesheet_uom", {
            component: GridTimesheetUOM,
            formatter,
        });

        if (!registry.category("formatters").contains("timesheet_uom_timer")) {
            registry.category("formatters").add("timesheet_uom_timer", formatter);
        }
    },
};

registry.category("services").add("timesheet_grid_uom", timesheetGridUOMService);
