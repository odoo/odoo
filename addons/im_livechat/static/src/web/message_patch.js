/* @odoo-module */

import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, "im_livechat/web", {
    get hasAuthorClickable() {
        if (this.message.originThread?.channel?.channel_type === "livechat") {
            return this.message.author === this.message.originThread.correspondent;
        }
        return this._super();
    },
});
