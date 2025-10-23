import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    computeIsEmpty() {
        return super.computeIsEmpty() && !this.rating_id && !this.rating_value;
    },

    get removeParams() {
        return { ...super.removeParams, rating_value: false };
    },
});
