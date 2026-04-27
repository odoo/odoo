/** @odoo-module */

import { Message } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get editable() {
        if (this.thread?.channel_type === "whatsapp") {
            return false;
        }
        return super.editable;
    },
    /** @override */
    canReplyTo(thread) {
        return super.canReplyTo(thread) && !this.thread?.composer?.threadExpired;
    },
});
