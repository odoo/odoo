import { Message } from "@mail/core/common/message_model";
import { patchModel } from "@mail/model/export";

export const messagePatch = patchModel(Message, {
    setup() {
        super.setup(...arguments);
        /** @type {number|null|undefined} */
        this.rating_value = undefined;
        /** @type {Object|undefined} */
        this.rating_stats = undefined;
    },
});
