/** @odoo-module */

import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";

import { GridTimesheetTimerHeader } from "@timesheet_grid/components/grid_timesheet_timer_header/grid_timesheet_timer_header";

patch(GridTimesheetTimerHeader.prototype, {
    getFieldInfo(fieldName) {
        const fieldInfo = super.getFieldInfo(fieldName);
        if (fieldName === "task_id") {
            fieldInfo.domain = Domain.and([
                fieldInfo.domain || [],
                [["is_timeoff_task", "=", false]],
            ]).toString();
        }
        return fieldInfo;
    },
});
