/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TimesheetGridDataPoint } from "@timesheet_grid/views/timesheet_grid/timesheet_grid_model";

patch(TimesheetGridDataPoint.prototype, {
    get timesheetWorkingHoursPromises() {
        const promises = super.timesheetWorkingHoursPromises;
        promises.push(this._fetchWorkingHoursData("so_line"));
        return promises;
    },
});
