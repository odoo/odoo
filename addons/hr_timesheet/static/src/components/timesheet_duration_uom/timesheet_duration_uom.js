import { registry } from "@web/core/registry";
import { TimesheetUOM } from "../timesheet_uom/timesheet_uom";

export class TimesheetDurationUOM extends TimesheetUOM {
    /**
     * @override
     */
    getTimesheetComponent(fieldName) {
        if (fieldName === "float_time") {
            fieldName = "time_hour_uom";
        }
        return super.getTimesheetComponent(fieldName);
    }
}

export const timesheetDurationUOM = {
    component: TimesheetDurationUOM,
};

registry.category("fields").add("timesheet_duration_uom", timesheetDurationUOM);
