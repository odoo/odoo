/** @odoo-module */

import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";
import { TimesheetGridDataPoint } from "@timesheet_grid/views/timesheet_grid/timesheet_grid_model";

patch(TimesheetGridDataPoint.prototype, {
    /**
     * @override
     */
    _getPreviousWeekTimesheetDomain() {
        return Domain.and([super._getPreviousWeekTimesheetDomain(), [["holiday_id", "=", false], ["global_leave_id", "=", false]]]);
    },

    /**
     * @override
     */
    _getFavoriteTaskDomain() {
        return Domain.and([super._getFavoriteTaskDomain(), [["is_timeoff_task", "=", false]]]);
    },
});
