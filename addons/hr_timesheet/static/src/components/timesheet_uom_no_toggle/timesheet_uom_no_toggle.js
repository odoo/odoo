import { registry } from "@web/core/registry";

import { TimesheetUOM, timesheetUOM } from "../timesheet_uom/timesheet_uom";

export class TimesheetUOMNoToggle extends TimesheetUOM {
    /**
     * @override
     */
    getTimesheetComponent(fieldName) {
        if (fieldName === "float_toggle") {
            fieldName = "float_factor"
        }
        return super.getTimesheetComponent(fieldName);
    }
}

export const timesheetUOMNoToggle = {
    ...timesheetUOM,
    component: TimesheetUOMNoToggle,
};

registry.category("fields").add("timesheet_uom_no_toggle", timesheetUOMNoToggle);
