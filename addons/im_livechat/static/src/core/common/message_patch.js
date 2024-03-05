import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get authorName() {
        if (
            this.message.author?.user_livechat_username &&
            this.message.thread.channel_type === "livechat"
        ) {
            return this.message.author.user_livechat_username;
        }
        return super.authorName;
    },
});
