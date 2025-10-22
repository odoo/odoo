import { DiscussContent } from "@mail/core/public_web/discuss_content";

import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    get isLivechatChannel() {
        return this.thread.channel_type === "livechat";
    },
    get showThreadAvatar() {
        return this.isLivechatChannel || super.showThreadAvatar;
    },
    get showImStatus() {
        return this.isLivechatChannel || super.showImStatus;
    },
});
