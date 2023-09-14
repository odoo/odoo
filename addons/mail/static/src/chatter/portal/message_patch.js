/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get canReplyTo() {
        return false;
    },

    get canToggleStar() {
        return false;
    },

    get canViewReactions() {
        return false;
    },

    hasAuthorClickable() {
        return false;
    },
});
