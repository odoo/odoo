/* @odoo-module */

import { Message } from "@mail/core/message_model";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, "discuss", {
    /**
     * @override
     */
    get editableInThread() {
        return this._super() || this.resModel === "discuss.channel";
    },
    /**
     * @override
     */
    get isHighlightedFromMention() {
        return this.isSelfMentioned && this.resModel === "discuss.channel";
    },
    /**
     * @override
     */
    get isNotification() {
        return this.type === "notification" && this.resModel === "discuss.channel";
    },
});
