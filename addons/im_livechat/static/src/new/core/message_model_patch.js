/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/message_model";

patch(Message.prototype, "im_livechat", {
    get isSelfAuthored() {
        if (this.originThread.type !== "livechat") {
            return this._super();
        }
        return this.author?.id !== this.originThread.operator?.id;
    },

    get hasActions() {
        return this.originThread.type !== "livechat" && this._super();
    },
});
