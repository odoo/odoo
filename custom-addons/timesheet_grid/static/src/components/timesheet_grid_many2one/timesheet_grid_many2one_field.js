/** @odoo-module */

import { registry } from "@web/core/registry";
import { Many2OneGridRow, many2OneGridRow } from "@web_grid/components/many2one_grid_row/many2one_grid_row";
import { TimesheetOvertimeIndication } from "../timesheet_overtime_indication/timesheet_overtime_indication";
import { useTimesheetOvertimeProps } from "../../hooks/useTimesheetOvertimeProps";

export class TimesheetGridMany2OneGridRow extends Many2OneGridRow {
    static template = "timesheet_grid.TimesheetGridMany2OneGridRow";

    static components = {
        ...Many2OneGridRow.components,
        TimesheetOvertimeIndication,
    };

    static props = {
        ...Many2OneGridRow.props,
        workingHours: { type: Object, optional: true },
    };

    setup() {
        super.setup(...arguments);
        this.timesheetOvertimeProps = useTimesheetOvertimeProps();
    }

    get overtimeProps() {
        return {
            ...this.timesheetOvertimeProps.props,
            name: this.props.name,
        };
    }
}

export const timesheetGridMany2OneGridRow = {
    ...many2OneGridRow,
    component: TimesheetGridMany2OneGridRow,
};

registry.category("grid_components").add("timesheet_many2one", timesheetGridMany2OneGridRow);
