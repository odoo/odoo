import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get authorAvatarUrl() {
        if (this.message.author_avatar_url) {
            return this.message.author_avatar_url;
        }
        if (
            this.store.env.services["portal.chatter"]?.token &&
            this.message.thread.model !== "discuss.channel"
        ) {
            return `/mail/avatar/mail.message/${this.message.id}/author_avatar/50x50?access_token=${this.store.env.services["portal.chatter"].token}`;
        }
        return super.authorAvatarUrl;
    },
});
