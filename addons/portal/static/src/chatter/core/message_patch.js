import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get canReplyTo() {
        if (this.env.inChatter) {
            return false;
        }
        return super.canReplyTo;
    },

    get canToggleStar() {
        if (this.env.inChatter) {
            return false;
        }
        return super.canToggleStar;
    },

    get editable() {
        if (this.env.inChatter) {
            return false;
        }
        return super.editable;
    },

    get quickActionCount() {
        if (this.env.inChatter) {
            return 1;
        }
        return super.quickActionCount;
    },
});
