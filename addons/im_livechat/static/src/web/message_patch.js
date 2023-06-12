/* @odoo-module */

import { Message } from "@mail/core/common/message";
import "@mail/discuss/core/web/message_patch"; // dependency ordering

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, "im_livechat/web", {
    get hasOpenChatFeature() {
        return this.message.originThread?.channel?.channel_type === "livechat"
            ? false
            : this._super();
    },
});
