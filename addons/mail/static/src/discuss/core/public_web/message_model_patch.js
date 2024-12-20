import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/model/record";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.linkedSubChannel = Record.one("Thread", { inverse: "from_message_id" });
        this.started_poll_id = Record.one("discuss.poll", { inverse: "start_message_id" });
        this.ended_poll_id = Record.one("discuss.poll", { inverse: "end_message_id" });
    },
});
