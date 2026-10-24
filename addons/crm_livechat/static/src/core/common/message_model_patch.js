import { Message } from "@mail/core/common/message_model";
import { patchModel } from "@mail/model/export";

export const messagePatch = patchModel(Message, {
    get notificationHidden() {
        if (this.notificationType === "create-lead" && this.store.self_user?.share !== false) {
            return true;
        }
        return super.notificationHidden;
    },
});
