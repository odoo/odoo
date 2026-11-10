import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get notificationHidden() {
        if (
            this.notificationType === "create-lead" &&
            (this.store.self_user?.share !== false ||
                this.channel_id?.selfMemberType === "visitor")
        ) {
            return true;
        }
        return super.notificationHidden;
    },
});
