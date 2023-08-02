/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Thread.prototype, {
    chatbotScriptId: null,

    get isChannel() {
        return this.type === "livechat" || super.isChannel;
    },

    get isChatChannel() {
        return this.type === "livechat" || super.isChatChannel;
    },

    get isLastMessageFromCustomer() {
        if (this.type !== "livechat") {
            return super.isLastMessageFromCustomer;
        }
        return this.newestMessage?.isSelfAuthored;
    },

    get imgUrl() {
        if (this.type !== "livechat") {
            return super.imgUrl;
        }
        return `${session.origin}/im_livechat/operator/${this.operator.id}/avatar`;
    },
});
