import { Message } from "@mail/core/common/message_model";
import { fields, patchModel } from "@mail/model/export";

export const messagePatch = patchModel(Message, {
    setup() {
        super.setup(...arguments);
        this.rating_id = fields.One("rating.rating");
    },

    computeIsEmpty() {
        return super.computeIsEmpty() && !this.rating_id && !this.rating_value;
    },

    get removeParams() {
        return { ...super.removeParams, rating_value: false };
    },
});
