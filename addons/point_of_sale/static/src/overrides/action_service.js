import { patch } from "@web/core/utils/patch";
import { actionService } from "@web/webclient/actions/action_service";

patch(actionService, {
    start(env) {
        // The action service wants to open the majority of links in the main container, not in new dialog.
        // The problem is that in pos we don't have the main container, so the links are simply not opened.
        // This is a workaround to always open links in new dialogs.
        const superReturn = super.start(env);
        return {
            ...superReturn,
            doAction: async (actionRequest, options = {}) => {
                if (
                    document.body.classList.contains("modal-open") &&
                    typeof actionRequest === "object"
                ) {
                    actionRequest.target = "new";
                }
                return superReturn.doAction(actionRequest, options);
            },
        };
    },
});
