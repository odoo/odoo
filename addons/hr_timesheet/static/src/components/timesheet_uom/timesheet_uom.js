import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { TimesheetUOMPlugin } from "@hr_timesheet/services/timesheet_uom_plugin";

import { Component, useProps, usePlugin } from "@odoo/owl";

export class TimesheetUOM extends Component {
    static template = "hr_timesheet.TimesheetUOM";

    // Make 'record' optional since this component can be called elsewhere and doesn't
    // use it.
    props = useProps({
        ...standardFieldProps,
        record: standardFieldProps.record.optional(),
    });
    timesheetUOMPlugin = usePlugin(TimesheetUOMPlugin);

    /**
     * @param {string} fieldName
     */
    getTimesheetComponent(fieldName) {
        return this.timesheetUOMPlugin.getTimesheetComponent(fieldName);
    }
}

export const timesheetUOM = {
    component: TimesheetUOM,
};

registry.category("fields").add("timesheet_uom", timesheetUOM);
