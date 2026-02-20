import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.rating_id = fields.One("rating.rating", { inverse: "message_id" });
    },

    computeIsEmpty() {
        return super.computeIsEmpty() && !this.rating_id;
    },

    get removeParams() {
        return { ...super.removeParams, rating_value: false };
    },
});
