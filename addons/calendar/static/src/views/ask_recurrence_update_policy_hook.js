import { useService } from "@web/core/utils/hooks";
import { AskRecurrenceUpdatePolicyDialog } from "@calendar/views/ask_recurrence_update_policy_dialog";

export function askRecurrenceUpdatePolicy(dialogService) {
    return new Promise((resolve) => {
        dialogService.add(AskRecurrenceUpdatePolicyDialog, {
            confirm: resolve,
        }, {
            onClose: resolve.bind(null, false),
        });
    });
}

export function useAskRecurrenceUpdatePolicy() {
    const dialogService = useService("dialog");
    return askRecurrenceUpdatePolicy.bind(null, dialogService);
}
