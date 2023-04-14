/** @odoo-module */

import { Thread } from "@mail/core/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "im_livechat", {
    get hasMemberList() {
        return this.type !== "livechat" && this._super();
    },

    get allowOpenInDiscuss() {
        return this.type !== "livechat" && this._super();
    },

    get hasNewMessageSeparator() {
        return this.type !== "livechat" && this._super();
    },
});
