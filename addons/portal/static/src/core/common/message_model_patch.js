import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
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
