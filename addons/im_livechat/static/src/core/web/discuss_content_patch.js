import { DiscussContent } from "@mail/core/public_web/discuss_content";

import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    actionPanelAutoOpenFn() {
        if (!this.threadActions.activeAction) {
            if (this.store.discuss.isLivechatInfoPanelOpenByDefault) {
                this.threadActions.actions.find((a) => a.id === "livechat-info")?.open();
            }
            return;
        }
        super.actionPanelAutoOpenFn();
    },
});
