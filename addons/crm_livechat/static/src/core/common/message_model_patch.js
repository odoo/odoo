import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get notificationHidden() {
        if (
            this.notificationType === "create-lead" &&
            this.channel_id?.self_member_id?.livechat_member_type === "visitor"
        ) {
            return true;
        }
        return super.notificationHidden;
    },
});
