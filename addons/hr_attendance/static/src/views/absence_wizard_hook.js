/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

export function useAbsenceManagementWizard() {
    const action = useService("action");

    return (rulesetId, ruleId) => {
        action.doAction({
            name: "Absence Management Wizard",
            type: "ir.actions.act_window",
            res_model: "hr.attendance.absence.management.wizard",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
            context: {
                default_ruleset_id: rulesetId,
                default_rule_id: ruleId,
            },
        });
    };
}
