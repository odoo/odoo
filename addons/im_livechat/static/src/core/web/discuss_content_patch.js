import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    actionPanelAutoOpenFn() {
        if (!this.threadActions.activeAction) {
            if (this.store.discuss.isLivechatInfoPanelOpenByDefault) {
                this.threadActions.actions.find((a) => a.id === "livechat-info")?.actionPanelOpen();
            }
            return;
        }
        super.actionPanelAutoOpenFn();
    },
    get threadDescriptionAttClass() {
        return {
            ...super.threadDescriptionAttClass,
            "text-warning":
                this.thread.channel?.livechat_status === "need_help" && this.thread.description,
        };
    },
});
