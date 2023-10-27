/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

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
        return url(`/im_livechat/operator/${this.operator.id}/avatar`);
    },
});
