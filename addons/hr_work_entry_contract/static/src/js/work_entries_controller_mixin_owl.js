/** @odoo-module **/

import { serializeDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";

export function useWorkEntry() {
    const orm = useService("orm");
    const action = useService("action");

    function getEmployeeIds(model) {
        const getEmployeeIdFromRecord = (record) => {
            return record.rawRecord.employee_id[0];
        }

        const groups = Object.values(model.records).reduce((groups, record) => {
            groups.add(getEmployeeIdFromRecord(record));
            return groups;
        }, new Set());
        return Array.from(groups);
    }

    function onRegenerateWorkEntries(model) {
        const employeeIds = getEmployeeIds(model);
        action.doAction('hr_work_entry_contract.hr_work_entry_regeneration_wizard_action', {
            additionalContext: {
                default_employee_ids: employeeIds,
                date_start: serializeDate(model.data.range.start),
                date_end: serializeDate(model.data.range.end),
            }
        });
    }

    function generateWorkEntries(start, end) {
        return orm.call(
            'hr.employee',
            'generate_work_entries',
            [[], serializeDate(start), serializeDate(end)]
        );
    }

    return {
        onRegenerateWorkEntries,
        generateWorkEntries
    }
}