import { registry } from "@web/core/registry";
import { TimesheetUOM } from "../timesheet_uom/timesheet_uom";
import { TimeHourField } from "../time_hour_field/time_hour_field";

export class TimesheetDurationUOM extends TimesheetUOM {
    static components = {
        ...TimesheetUOM.components,
        TimeHourField,
    };
    get timesheetComponent() {
        if (this.timesheetUOMService.timesheetWidget === "float_time") {
            return this.timesheetUOMService.getTimesheetComponent("time_hour_uom");
        }
        return super.timesheetComponent;
    }
}

export const timesheetDurationUOM = {
    component: TimesheetDurationUOM,
};

registry.category("fields").add("timesheet_duration_uom", timesheetDurationUOM);
