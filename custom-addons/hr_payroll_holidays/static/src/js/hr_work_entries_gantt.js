/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TimeOffToDeferWarning, useTimeOffToDefer } from "@hr_payroll_holidays/views/hooks";
import { WorkEntriesGanttController } from '@hr_work_entry_contract_enterprise/work_entries_gantt_controller';

patch(WorkEntriesGanttController.prototype, {
    setup() {
        super.setup(...arguments);
        this.timeOff = useTimeOffToDefer();
    }
});

patch(WorkEntriesGanttController, {
    components: { ...WorkEntriesGanttController.components, TimeOffToDeferWarning },
    template: "hr_payroll_holidays.WorkEntriesGanttController"
});
