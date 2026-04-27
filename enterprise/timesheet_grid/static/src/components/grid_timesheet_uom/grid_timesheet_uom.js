/** @odoo-module */

import { registry } from "@web/core/registry";

import { GridCell, standardGridCellProps } from "@web_grid/components/grid_cell";
import { FloatFactorGridCell } from "@web_grid/components/float_factor_grid_cell";
import { FloatToggleGridCell } from "@web_grid/components/float_toggle_grid_cell";
import { FloatTimeGridCell } from "@web_grid/components/float_time_grid_cell";

import { TimesheetUOM } from "@hr_timesheet/components/timesheet_uom/timesheet_uom";

export class GridTimesheetUOM extends TimesheetUOM {
    static props = {
        ...standardGridCellProps,
    };
    static defaultProps = {
        readonly: true,
        editMode: false,
    };

    static components = { GridCell, FloatFactorGridCell, FloatToggleGridCell, FloatTimeGridCell };

    get timesheetComponent() {
        return registry.category("grid_components").get(this.timesheetUOMService.timesheetWidget, {
            component: GridCell,
            formatter: this.timesheetUOMService.formatter,
        }).component;
    }
}
