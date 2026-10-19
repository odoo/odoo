import { patch } from "@web/core/utils/patch";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

patch(ActionPlugin.prototype, {
    setup() {
        super.setup();
        // The action service wants to open the majority of links in the main container, not in new dialog.
        // The problem is that in pos we don't have the main container, so the links are simply not opened.
        // This is a workaround to always open links in new dialogs.
        const superDoAction = this.doAction;
        this.doAction = async (actionRequest, options = {}) => {
            if (
                document.body.classList.contains("modal-open") &&
                typeof actionRequest === "object"
            ) {
                actionRequest.target = "new";
            }
            return superDoAction(actionRequest, options);
        };
    },
});
