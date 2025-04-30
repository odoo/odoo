import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

patch(Message, {
    components: { ...Message.components },
});

patch(Message.prototype, {
    get isAlignedRight() {
        return !this.env.messageCard && super.isAlignedRight;
    },
    get shouldDisplayAuthorName() {
        if (this.env.messageCard) {
            return true;
        }
        return super.shouldDisplayAuthorName;
    },
});
