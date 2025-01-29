import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    skipEdit(body, updateData) {
        return super.skipEdit(...arguments) && !updateData.rating_value;
    },
    
    computeIsEmpty() {
        return super.computeIsEmpty() && !this.rating_id;
    },

    get removeParams() {
        return {
            ...super.removeParams,
            rating_value: false,
        };
    },
};
patch(Message.prototype, messagePatch);
