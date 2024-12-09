import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    skipEdit(updateData) {
        return super.skipEdit(...arguments) && this.rating_id?.rating === updateData.rating_value;
    },
};
patch(Message.prototype, messagePatch);
