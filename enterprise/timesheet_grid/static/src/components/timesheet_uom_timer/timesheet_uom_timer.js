/** @odoo-module */

import { registry } from "@web/core/registry";
import { FloatFactorField } from "@web/views/fields/float_factor/float_factor_field";
import { FloatToggleField } from "@web/views/fields/float_toggle/float_toggle_field";

import { TimesheetUOM, timesheetUOM } from "@hr_timesheet/components/timesheet_uom/timesheet_uom";
import { TimesheetUOMHourTimer } from "../timesheet_uom_hour_timer/timesheet_uom_hour_timer";

class TimesheetUOMTimer extends TimesheetUOM {
    static components = {
        ...TimesheetUOM.components,
        FloatFactorField,
        FloatToggleField,
        TimesheetUOMHourTimer,
    };
    get timesheetComponent() {
        if (this.timesheetUOMService.timesheetWidget === "float_time") {
            return this.timesheetUOMService.getTimesheetComponent("timesheet_uom_hour_timer");
        }
        return super.timesheetComponent;
    }
}

// As we replace FloatTimeField by TimesheetUOMHourTimer, we remove it from the components that we get from TimesheetUOM.
delete TimesheetUOMTimer.components.FloatTimeField;

registry.category("fields").add("timesheet_uom_timer", {
    ...timesheetUOM,
    component: TimesheetUOMTimer,
    additionalClasses: ["o_field_timesheet_uom"],
});
