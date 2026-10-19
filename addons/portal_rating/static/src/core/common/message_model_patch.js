import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {number|null|undefined} */
        this.rating_value = undefined;
        /** @type {Object|undefined} */
        this.rating_stats = undefined;
    },
});
