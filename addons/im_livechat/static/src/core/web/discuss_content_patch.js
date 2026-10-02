import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    autoOpenPanel() {
        const livechatInfoAction = this.threadActions.actions.find((a) => a.id === "livechat-info");
        if (livechatInfoAction && this.store.discuss.isLivechatInfoPanelOpenByDefault) {
            livechatInfoAction.openPanel();
        } else {
            super.autoOpenPanel();
        }
    },
});
