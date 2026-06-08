import { DiscussContent } from "@mail/core/public_web/discuss_content";

import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    get isLivechatChannel() {
        return this.thread.channel?.channel_type === "livechat";
    },
    get showThreadAvatar() {
        return this.isLivechatChannel || super.showThreadAvatar;
    },
});
