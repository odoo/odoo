import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    actionPanelAutoOpenFn() {
        if (!this.threadActions.activeAction) {
            this.threadActions.actions.find((a) => a.id === "livechat-info")?.open();
        }
        super.actionPanelAutoOpenFn();
    },
});
