import { ChatBubble } from "@mail/core/common/chat_bubble";

import { patch } from "@web/core/utils/patch";

patch(ChatBubble.prototype, {
    get showImStatus() {
        return (
            super.showImStatus &&
            !(this.thread?.correspondent?.livechat_member_type === "bot" && this.env.embedLivechat)
        );
    },
});
