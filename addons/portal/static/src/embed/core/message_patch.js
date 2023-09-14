/* @odoo-module */

import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get authorAvatarUrl() {
        if (this.message.author_avatar_url) {
            return this.message.author_avatar_url;
        }
        return super.authorAvatarUrl;
    },
});
