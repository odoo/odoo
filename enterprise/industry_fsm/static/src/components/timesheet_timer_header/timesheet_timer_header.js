import { TimesheetTimerHeader } from "@timesheet_grid/components/timesheet_timer_header/timesheet_timer_header";
import { patch } from "@web/core/utils/patch";

patch(TimesheetTimerHeader.prototype, {
    getFieldType(fieldName) {
        let fieldType = super.getFieldType(fieldName);
        if (fieldName === "task_id" && this.viewType === "list") {
            fieldType = `list.${fieldType}`;
        }
        return fieldType;
    },
});
