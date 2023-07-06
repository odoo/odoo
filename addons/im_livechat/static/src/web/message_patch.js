/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core_ui/message";

patch(Message.prototype, "im_livechat/web", {
    get hasAuthorClickable() {
        if (this.message.originThread?.channel?.channel_type === "livechat") {
            return this.message.author === this.message.originThread.correspondent;
        }
        return this._super();
    },
    get hasOpenChatFeature() {
        if (this.message.originThread?.channel?.channel_type === "livechat") {
            return false;
        }
        return this._super();
    },
});
