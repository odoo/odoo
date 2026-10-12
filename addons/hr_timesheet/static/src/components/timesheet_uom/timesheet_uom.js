import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, useProps } from "@odoo/owl";

export class TimesheetUOM extends Component {
    static template = "hr_timesheet.TimesheetUOM";

    // Make 'record' optional since this component can be called elsewhere and doesn't
    // use it.
    props = useProps({
        ...standardFieldProps,
        record: standardFieldProps.record.optional(),
    });

    setup() {
        this.timesheetUOMService = useService("timesheet_uom");
    }

    /**
     * @param {string} fieldName
     */
    getTimesheetComponent(fieldName) {
        return this.timesheetUOMService.getTimesheetComponent(fieldName);
    }
}

export const timesheetUOM = {
    component: TimesheetUOM,
};

registry.category("fields").add("timesheet_uom", timesheetUOM);
