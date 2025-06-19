import { Discuss } from "@mail/core/public_web/discuss";
import { patch } from "@web/core/utils/patch";

patch(Discuss.prototype, {
    actionPanelAutoOpenFn() {
        if (!this.threadActions.activeAction) {
            this.threadActions.actions.find((a) => a.id === "livechat-info")?.open();
        }
        super.actionPanelAutoOpenFn();
    },
});
