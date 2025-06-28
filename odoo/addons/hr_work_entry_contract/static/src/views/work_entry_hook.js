/** @odoo-module **/

import { serializeDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";

export function useWorkEntry({ getEmployeeIds, getRange, onClose}) {
    const orm = useService("orm");
    const action = useService("action");

    return {
        onRegenerateWorkEntries: () => {
            const { start, end } = getRange();
            action.doAction('hr_work_entry_contract.hr_work_entry_regeneration_wizard_action', {
                additionalContext: {
                    default_employee_ids: getEmployeeIds(),
                    date_start: serializeDate(start),
                    date_end: serializeDate(end),
                }, onClose: onClose
            });
        },
        generateWorkEntries: () => {
            const { start, end } = getRange();
            return orm.call(
                'hr.employee',
                'generate_work_entries',
                [[], serializeDate(start), serializeDate(end)]
            );
        },
    }
}
