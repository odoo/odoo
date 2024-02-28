/** @odoo-module */

import { registry } from "@web/core/registry";

import { TimesheetUOM } from "../timesheet_uom/timesheet_uom";


export class TimesheetUOMNoToggle extends TimesheetUOM {

    get timesheetWidget() {
        const timesheetWidget = super.timesheetWidget;
        return timesheetWidget !== "float_toggle" ? timesheetWidget : "float_factor";
    }

}

// As FloatToggleField won't be used by TimesheetUOMNoToggle, we remove it from the components that we get from TimesheetUOM.
delete TimesheetUOMNoToggle.components.FloatToggleField;

registry.category("fields").add("timesheet_uom_no_toggle", TimesheetUOMNoToggle);
