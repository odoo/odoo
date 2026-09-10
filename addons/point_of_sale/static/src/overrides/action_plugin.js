import { patch } from "@web/core/utils/patch";
import { ActionManagerPlugin } from "@web/webclient/actions/action_plugin";

patch(ActionManagerPlugin.prototype, {
    setup() {
        super.setup();
        // The action service wants to open the majority of links in the main container, not in new dialog.
        // The problem is that in pos we don't have the main container, so the links are simply not opened.
        // This is a workaround to always open links in new dialogs.
        const superDoAction = this.manager.doAction.bind(this.manager);
        this.manager.doAction = async (actionRequest, options = {}) => {
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
