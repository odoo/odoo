import { Message } from "@mail/core/common/message_model";
import { patchModel } from "@mail/model/export";

export const messagePatch = patchModel(Message, {
    setup() {
        super.setup(...arguments);
        /** @type {boolean|undefined} */
        this.is_internal = undefined;
        /** @type {boolean|undefined} */
        this.is_message_subtype_note = undefined;
        /** @type {string|undefined} */
        this.published_date_str = undefined;
    },
});
