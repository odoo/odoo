import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/model/misc";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.threadAsUserNotification = fields.One("Thread", {
            compute() {
                if (this.message_type === "user_notification") {
                    return this.thread;
                }
            },
        });
    },
});
