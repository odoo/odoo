import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.rating_id = Record.one("rating.rating");
    },

    computeIsEmpty() {
        return super.computeIsEmpty() && !this.rating_id && !this.rating_value;
    },

     async remove() {
        const data = await super.remove();
        this.rating_value = false;
        return data;
    },

    get removeParams() {
        return { ...super.removeParams, rating_value: false };
    },
});
