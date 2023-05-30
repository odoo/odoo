/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Thread.prototype, "im_livechat", {
    chatbotScriptId: null,

    get isChannel() {
        return this.type === "livechat" || this._super();
    },

    get isChatChannel() {
        return this.type === "livechat" || this._super();
    },

    get isLastMessageFromCustomer() {
        if (this.type !== "livechat") {
            return this._super();
        }
        return this.newestMessage?.isSelfAuthored;
    },

    get imgUrl() {
        if (this.type !== "livechat") {
            return this._super();
        }
        return `${session.origin}/im_livechat/operator/${this.operator.id}/avatar`;
    },
});
