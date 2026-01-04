import { ChatBubble } from "@mail/core/common/chat_bubble";

import { patch } from "@web/core/utils/patch";

patch(ChatBubble.prototype, {
    get showImStatus() {
        if (this.thread?.self_member_id?.livechat_member_type === "visitor") {
            return false;
        }
        return super.showImStatus;
    },
});
