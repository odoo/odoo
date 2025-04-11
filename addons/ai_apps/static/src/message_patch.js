import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";


patch(Message.prototype, {
    get quickActionCount() {
        if (this.props.thread.channel_type !== "ai_composer") {
            return super.quickActionCount;
        }
        return 3;
    },
});
