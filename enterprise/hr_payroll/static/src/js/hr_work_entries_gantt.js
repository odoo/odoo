import { patch } from "@web/core/utils/patch";
import { useWorkEntryPayslip } from '@hr_payroll/views/work_entry_calendar/work_entry_calendar_hook';
import { WorkEntriesGanttController } from "@hr_work_entry_contract_enterprise/work_entries_gantt_controller";

patch(WorkEntriesGanttController.prototype, {
    setup() {
        super.setup(...arguments);
        this.onGeneratePayslips = useWorkEntryPayslip({
            getEmployeeIds: () => this.getActiveEmployeeIds(),
            getRange: () => this.model.getRange(),
        });
    },

    checkConflicts() {
        return this.model.data.records.some((record) => record.state === "conflict");
    },

    getActiveEmployeeIds() {
        const employeeIds = new Set();
        for (const rec of this.model.data.records) {
            if (rec.employee_id) {
                employeeIds.add(rec.employee_id[0]);
            }
        }
        return [...employeeIds];
    },

    getShowGeneratePayslipsButton() {
        return this.model.data.records.some((record) => record.state !== "validated");
    },
});
