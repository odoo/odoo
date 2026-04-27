/** @odoo-module **/

import { PlanningAskRecurrenceUpdateDialog } from "./planning_ask_recurrence_update_dialog";

export function planningAskRecurrenceUpdate(dialogService) {
    return new Promise((resolve) => {
        dialogService.add(PlanningAskRecurrenceUpdateDialog, {
            confirm: resolve,
        }, {
            onClose: resolve.bind(null, false),
        });
    });
}
