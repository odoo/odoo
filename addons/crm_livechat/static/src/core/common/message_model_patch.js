import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get notificationHidden() {
        if (
            this.notificationType === "create-lead" &&
            this.store.has_access_create_lead === false
        ) {
            return true;
        }
        return super.notificationHidden;
    },
});
