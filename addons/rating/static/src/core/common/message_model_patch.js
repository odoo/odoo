import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.rating_id = Record.one("rating.rating");
    },
});
