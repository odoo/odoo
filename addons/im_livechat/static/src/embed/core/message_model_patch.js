/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/message_model";
import { session } from "@web/session";

patch(Message.prototype, "im_livechat", {
    get isSelfAuthored() {
        if (this.originThread.type !== "livechat") {
            return this._super();
        }
        return !this.author || this.author?.id === session.livechatData.options.current_partner_id;
    },
});
