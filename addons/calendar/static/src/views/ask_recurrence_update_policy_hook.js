/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { AskRecurrenceUpdatePolicyDialog } from "@calendar/views/ask_recurrence_update_policy_dialog";

export function askRecurrenceUpdatePolicy(dialogService, acceptedUpdates) {
    return new Promise((resolve) => {
        dialogService.add(AskRecurrenceUpdatePolicyDialog, {
            confirm: resolve,
            acceptedUpdates: acceptedUpdates
        }, {
            onClose: resolve.bind(null, false),
        });
    });
}

export function useAskRecurrenceUpdatePolicy() {
    const dialogService = useService("dialog");
    return askRecurrenceUpdatePolicy.bind(null, dialogService);
}
