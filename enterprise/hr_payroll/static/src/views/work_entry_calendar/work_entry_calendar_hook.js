/** @odoo-module **/

import { serializeDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";

export function useWorkEntryPayslip({ getEmployeeIds, getRange }) {
    const action = useService("action");
    return () => {
        const { start, end } = getRange();
        action.doAction("hr_payroll.action_generate_payslips_from_work_entries", {
            additionalContext: {
                default_date_start: serializeDate(start),
                default_date_end: serializeDate(end),
                active_employee_ids: getEmployeeIds()
            }
        });
    }
}
