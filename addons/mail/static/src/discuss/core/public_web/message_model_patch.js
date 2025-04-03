import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/model/misc";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.linkedSubChannel = fields.One("Thread", { inverse: "from_message_id" });
    },
});
