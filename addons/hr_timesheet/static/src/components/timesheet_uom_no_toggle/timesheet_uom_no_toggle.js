import { registry } from "@web/core/registry";

import { TimesheetUOM, timesheetUOM } from "../timesheet_uom/timesheet_uom";

export class TimesheetUOMNoToggle extends TimesheetUOM {
    get timesheetComponent() {
        if (this.timesheetUOMService.timesheetWidget === "float_toggle") {
            return this.timesheetUOMService.getTimesheetComponent("float_factor");
        }
        return super.timesheetComponent;
    }
}

// As FloatToggleField won't be used by TimesheetUOMNoToggle, we remove it from the components that we get from TimesheetUOM.
delete TimesheetUOMNoToggle.components.FloatToggleField;

export const timesheetUOMNoToggle = {
    ...timesheetUOM,
    component: TimesheetUOMNoToggle,
};

registry.category("fields").add("timesheet_uom_no_toggle", timesheetUOMNoToggle);
