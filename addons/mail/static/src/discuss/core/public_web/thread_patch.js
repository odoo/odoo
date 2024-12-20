import { Thread } from "@mail/core/common/thread";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    get orderedMessages() {
        const result = super.orderedMessages;
        if (this.props.thread.from_message_id) {
            if (this.props.order === "asc") {
                result.unshift(this.props.thread.from_message_id);
            } else {
                result.push(this.props.thread.from_message_id);
            }
        }
        return result;
    },
});
