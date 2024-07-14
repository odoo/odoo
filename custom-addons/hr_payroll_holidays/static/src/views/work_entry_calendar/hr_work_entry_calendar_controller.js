/** @odoo-module **/

import { TimeOffToDeferWarning, useTimeOffToDefer } from "@hr_payroll_holidays/views/hooks";
import { WorkEntryCalendarController } from "@hr_work_entry_contract/views/work_entry_calendar/work_entry_calendar_controller";
import { patch } from "@web/core/utils/patch";

patch(
    WorkEntryCalendarController.prototype,
    {
        setup() {
            super.setup(...arguments);
            this.timeOff = useTimeOffToDefer();
        },
    }
);
patch(WorkEntryCalendarController, {
    template: "hr_payroll_holidays.WorkEntryCalendarController",
    components: { ...WorkEntryCalendarController.components, TimeOffToDeferWarning },
});
