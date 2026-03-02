import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    actionPanelAutoOpenFn() {
        const livechatInfoAction = this.threadActions.actions.find((a) => a.id === "livechat-info");
        if (livechatInfoAction && this.store.discuss.isLivechatInfoPanelOpenByDefault) {
            livechatInfoAction.actionPanelOpen();
        } else {
            super.actionPanelAutoOpenFn();
        }
    },
    get threadTopicAttClass() {
        return {
            ...super.threadTopicAttClass,
            "text-muted":
                this.thread.channel?.livechat_status === "need_help" && this.thread.topic,
        };
    },
});
